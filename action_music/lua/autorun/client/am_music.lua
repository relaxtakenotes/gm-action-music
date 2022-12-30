local bosses = {"npc_combinegunship", "npc_hunter", "npc_helicopter", "npc_strider"}

local fade_time = CreateConVar("cl_am_fadetime_mult", "0.5", FCVAR_ARCHIVE, "How fast the music will change.", 0.01, 10)
local continue_songs = CreateConVar("cl_am_continue_songs", "1", FCVAR_ARCHIVE, "Continue songs where we left off.")
local volume_scale = CreateConVar("cl_am_volume", "0.5", FCVAR_ARCHIVE, "Volume. Epic.")
local force_type = CreateConVar("cl_am_force_type", "0", FCVAR_ARCHIVE, "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle)")

local last_type = ""
local timer_name_counter = 0
local amready = false

local current_channel = nil
local past_channel = nil
local current_song = nil
local channel_locked = false

local is_targeted = nil
local by_npc = nil

local songs = {}

//local function get_song_duration(path)
//	status, result = pcall(function() return tonumber(string.Trim(string.match(path, "_%d%d%d"), "_"), 10) end)
//	if status == true then return result end
//
//	status, result = pcall(function() return get_sound_duration(path) end)
//	if status == true then return result end
//	if status == false then return nil end // gmod will handle it later in gmodaudiochannel (badly but it will)
//end

local function parse_am()
	for i, search_path in ipairs({"sound/am_music/battle/", "sound/am_music/battle_intensive/", "sound/am_music/background/"}) do
		local files, _ = file.Find(search_path.."*", "GAME")
		for i, mfile in ipairs(files) do
			local song = {}

			song.path = search_path .. mfile
			//song.duration = get_song_duration(song.path)
			song.last_duration = 0
			local split_str = string.Split(search_path, "/")
			song.typee = split_str[#split_str-1]
			song.index = #songs[song.typee]+1

			table.insert(songs[song.typee], song)
		end		
	end
end

local function parse_nombat()
	local _, directories = file.Find("sound/nombat/*", "GAME")
	for i, directory in ipairs(directories) do
		local files, _ = file.Find("sound/nombat/"..directory.."/*", "GAME")
		for j, mfile in ipairs(files) do
			local song = {}

			song.path = "sound/nombat/"..directory.."/"..mfile
			//song.duration = get_song_duration(song.path)
			song.last_duration = 0
			if string.StartWith(mfile, "c") then song.typee = "battle" else song.typee = "background" end
			song.index = #songs[song.typee]+1

			table.insert(songs[song.typee], song)
		end		
	end
end

local function parse_dynamo(dirr)
	for i, search_path in ipairs({"sound/"..dirr.."/ambient/", "sound/"..dirr.."/combat/bosses/", "sound/"..dirr.."/combat/cops/", "sound/"..dirr.."/combat/soldiers/", "sound/"..dirr.."/combat/aliens/"}) do
		local files, _ = file.Find(search_path.."*", "GAME")
		for i, mfile in ipairs(files) do
			local song = {}

			song.path = search_path .. mfile

			//song.duration = get_song_duration(song.path)
			song.last_duration = 0
			local split_str = string.Split(search_path, "/")
			song.typee = split_str[#split_str-1]
			if song.typee == "ambient" then song.typee = "background" end
			if song.typee == "bosses" then song.typee = "battle_intensive" end
			if song.typee == "aliens" then continue end // these are not good
			if song.typee == "cops" then song.typee = "battle" end
			if song.typee == "soldiers" then song.typee = "battle" end
			song.index = #songs[song.typee]+1

			table.insert(songs[song.typee], song)
		end		
	end
end

local function initialize_songs()
	songs["battle"] = {}
	songs["battle_intensive"] = {}
	songs["background"] = {}

	parse_am()
	parse_nombat()
	parse_dynamo("battlemusic")
	parse_dynamo("ayykyu_dynmus")

	amready = true
end

concommand.Add("cl_am_initialize_songs", function(ply, cmd, args)
	initialize_songs()
end)

local function fade_channel(channel, to)
	local from = channel:GetVolume()
	local lerp_t = 0

	timer_name_counter = timer_name_counter + 1
	local timer_name = "fade_timer"..timer_name_counter

	timer.Create(timer_name, 0, math.huge, function() 
		if not IsValid(channel) then return end

		lerp_t = math.min(1, lerp_t + fade_time:GetFloat() * FrameTime())

		channel:SetVolume(Lerp(lerp_t, from, to))

		if lerp_t == 1 then
			if to == 0 then channel:Stop() end
			timer.Remove(timer_name) 
		end
	end)
end

local function am_play(typee, delay, force)
	if not amready then return end
	if force_type:GetInt() == 1 then typee = "background" end
	if force_type:GetInt() == 2 then typee = "battle" end
	if force_type:GetInt() == 3 then typee = "battle_intensive" end
	if last_type == typee and not force then return end

	if songs[typee] == nil then
		print(typee)
		print("Important! There are no songs of type '"..typee.."'! Please install a pack that will fill that up.")
		return 
	end


	timer.Simple(delay, function()
		local song = songs[typee][math.random(#songs[typee])]

		if song == nil then return end

		if current_channel != nil then
			past_channel = current_channel
			songs[current_song.typee][current_song.index].last_duration = past_channel:GetTime()
			fade_channel(past_channel, 0)
		end

		sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
			print("Now playing: "..song.path.."!")

			current_channel = station
			current_song = song

			//if song.duration == nil then song.duration = current_channel:GetLength() end
			//if song.last_duration + 1 >= song.duration then song.last_duration = 0 end
			if continue_songs:GetBool() then current_channel:SetTime(song.last_duration, true) end

			current_channel:SetVolume(0)
			fade_channel(current_channel, 1 * volume_scale:GetFloat())

			channel_locked = false
		end)
	end)

	last_type = typee
end

net.Receive("am_threat_event", function()
	if not amready then return end
	is_targeted = net.ReadBool()
	by_npc = net.ReadEntity()
	if IsValid(by_npc) then by_npc = by_npc:GetClass() end

	if is_targeted and table.HasValue(bosses, by_npc) then
		am_play("battle_intensive", 0)
	elseif is_targeted then
		am_play("battle", 0)
	else
		am_play("background", 2)
	end

end)

concommand.Add("cl_am_reshuffle", function(ply, cmd, args)
	if not amready then return end
	if current_channel == nil then return end

	current_channel:Pause() // channel:stop() makes it null which later fucks up things :\

	print("Reshuffled. Get out of the exit menu to make it play if you're in singleplayer.")
end)

hook.Add("Think", "am_think", function()
	if not amready then return end
	if current_channel == nil then return end

	local state = current_channel:GetState()

	if (state == 0 or state == 2) and not channel_locked then
		current_song.last_duration = 0
		am_play(current_song.typee, 0, true)
		channel_locked = true
	end
end)

hook.Add("InitPostEntity", "am_initialize_songs", function() 
	initialize_songs()
end)
