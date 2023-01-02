local bosses = {"npc_combinegunship", "npc_hunter", "npc_helicopter", "npc_strider", "a_shit_ton_of_enemies"}

local fade_time = CreateConVar("cl_am_fadetime_mult", "0.5", FCVAR_ARCHIVE, "How fast the music will change.", 0.01, 10)
local continue_songs = CreateConVar("cl_am_continue_songs", "1", FCVAR_ARCHIVE, "Continue songs where we left off.")
local reset_last_duration = CreateConVar("cl_am_reshuffle_period", "60", FCVAR_ARCHIVE, "Shuffle some songs in a given period. (0 is disabled)")
local volume_scale = CreateConVar("cl_am_volume", "0.5", FCVAR_ARCHIVE, "Volume. Epic.")
local force_type = CreateConVar("cl_am_force_type", "0", FCVAR_ARCHIVE, "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle)")
local type_song = CreateConVar("cl_am_chat_print", "0", FCVAR_ARCHIVE, "Print music change to chat.")

local last_type = ""
local timer_name_counter = 0
local amready = false

local current_channel = nil
local past_channel = nil
local channel_locked = false

local last_forget_time = 0

local songs = {}
local current_song = nil
local chosen_songs = {}
chosen_songs["battle"] = NULL
chosen_songs["battle_intensive"] = NULL
chosen_songs["background"] = NULL

local is_targeted = nil
local by_npc = nil

local function parse_am()
	for i, search_path in ipairs({"sound/am_music/battle/", "sound/am_music/battle_intensive/", "sound/am_music/background/"}) do
		local files, _ = file.Find(search_path.."*", "GAME")
		for i, mfile in ipairs(files) do
			local song = {}

			song.path = search_path .. mfile
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

local function shuffle_chosen_songs()
	for key, item in pairs(chosen_songs) do
		if not songs[key] then continue end
		chosen_songs[key] = songs[key][math.random(#songs[key])]
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

	shuffle_chosen_songs()

	amready = true
end


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
	if channel_locked then return end
	if force_type:GetInt() == 1 then typee = "background" end
	if force_type:GetInt() == 2 then typee = "battle" end
	if force_type:GetInt() == 3 then typee = "battle_intensive" end
	if last_type == typee and not force then return end

	if chosen_songs[typee] == nil or chosen_songs[typee] == NULL then
		chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), "There are no songs of type ", typee, ". Please include something in it!")
		return 
	end

	channel_locked = true

	timer.Simple(delay, function()
		local song = chosen_songs[typee]

		if not continue_songs:GetBool() then song = songs[typee][math.random(#songs[typee])] end

		if song == nil then return end

		if current_channel != nil then
			past_channel = current_channel
			songs[current_song.typee][current_song.index].last_duration = past_channel:GetTime()
			fade_channel(past_channel, 0)
		end

		sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
			channel_locked = false
			local split_str = string.Split(song.path, "/")
			local name = string.StripExtension(split_str[#split_str])

			if type_song:GetBool() then
				chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), "Now playing: ", name)
			end

			if not station then 
				chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 50, 50), "Failed playing: ", name, "\n\t\t\tError Code: ", error_code, "\n\t\t\tError: ", error_string, "\n\t\t\tUsually any error can be resolved by making sure your title has no unicode characters. If you can't find any, simplify it.")
				return 
			end

			current_channel = station
			current_song = song

			if continue_songs:GetBool() then current_channel:SetTime(song.last_duration, true) end

			current_channel:SetVolume(0)
			fade_channel(current_channel, 1 * volume_scale:GetFloat())

		end)

	end)

	last_type = typee
end

net.Receive("am_threat_event", function()
	if not amready then return end
	is_targeted = net.ReadBool()
	by_npc = net.ReadString()

	if is_targeted and table.HasValue(bosses, by_npc) then
		am_play("battle_intensive", 0)
	elseif is_targeted then
		am_play("battle", 0)
	else
		am_play("background", 2)
	end

end)

hook.Add("Think", "am_think", function()
	if not amready then return end
	if current_channel == nil then return end
	if engine.TickCount() % 20 != 0 then return end

	local state = current_channel:GetState()

	if (state == 0 or state == 2) then
		current_song.last_duration = 0
		chosen_songs[current_song.typee] = songs[current_song.typee][math.random(#songs[current_song.typee])]
		am_play(current_song.typee, 0, true)
	end
end)

hook.Add("Think", "am_think_forget", function()
	if not reset_last_duration:GetBool() then return end
	if CurTime() - last_forget_time > reset_last_duration:GetInt() then
		last_forget_time = CurTime()
		shuffle_chosen_songs()
	end
end)

hook.Add("InitPostEntity", "am_initialize_songs", function() 
	initialize_songs()
end)

concommand.Add("cl_am_initialize_songs", function(ply, cmd, args)
	initialize_songs()
end)

concommand.Add("cl_am_reshuffle", function(ply, cmd, args)
	if not amready then return end
	if current_channel == nil then return end

	current_channel:Pause() // channel:stop() makes it null which later fucks up things :\

	shuffle_chosen_songs()

	chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), "Reshuffled!")
end)