local amready = false

am_current_song = nil
am_current_channel = nil
local past_channel = nil
local channel_locked = false

local songs = {}
local chosen_songs = {}
chosen_songs["battle"] = NULL
chosen_songs["battle_intensive"] = NULL
chosen_songs["background"] = NULL
chosen_songs["suspense"] = NULL

local last_type = ""
local timer_name_counter = 0
local last_forget_time = 0

local fade_time = CreateConVar("cl_am_fadetime_mult", "0.5", FCVAR_ARCHIVE, "How fast the music will change.", 0.01, 10)
local continue_songs = CreateConVar("cl_am_continue_songs", "1", FCVAR_ARCHIVE, "Continue songs where we left off.")
local reset_last_duration = CreateConVar("cl_am_reshuffle_period", "60", FCVAR_ARCHIVE, "Shuffle some songs in a given period. (0 is disabled)")
local force_type = CreateConVar("cl_am_force_type", "0", FCVAR_ARCHIVE, "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle). 4 - Suspense")
local type_song = CreateConVar("cl_am_chat_print", "0", FCVAR_ARCHIVE, "Print music change to chat.")

local am_enabled_global = CreateConVar("cl_am_enabled_global", "1", FCVAR_ARCHIVE, "Obvious!")
cvars.AddChangeCallback("cl_am_enabled_global", function(convar_name, value_old, value_new)
	if tonumber(value_new) == 0 and IsValid(am_current_channel) then am_current_channel:Stop() end
end)

local am_enabled = {}
local volume_scale = {}

for _, typee in ipairs({"battle", "background", "battle_intensive", "suspense"}) do
	volume_scale[typee] = CreateConVar("cl_am_volume_"..typee, "1", FCVAR_ARCHIVE, "Volume. Epic.")
	am_enabled[typee] = CreateConVar("cl_am_enabled_"..typee, "1", FCVAR_ARCHIVE, "Obvious!")

	cvars.AddChangeCallback("cl_am_volume_"..typee, function(convar_name, value_old, value_new)
		if tonumber(value_new) < 0.01 then print("Use cl_am_enabled for that.") volume_scale[typee]:SetFloat(tonumber(value_old)) return end
	    if am_current_song.typee == typee then am_current_channel:SetVolume(tonumber(value_new)) end
	end)
	
	cvars.AddChangeCallback("cl_am_enabled_"..typee, function(convar_name, value_old, value_new)
		if not am_current_song then return end
	    if am_current_song.typee == typee and tonumber(value_new) == 0 and IsValid(am_current_channel) then am_current_channel:Stop() end
	end)
end

local function parse_am()
	for i, search_path in ipairs({"sound/am_music/battle/", "sound/am_music/battle_intensive/", "sound/am_music/background/", "sound/am_music/suspense/"}) do
		local files, _ = file.Find(search_path.."*", "GAME")
		local split_str = string.Split(search_path, "/")
		for i, mfile in ipairs(files) do
			local song = {}

			song.path = search_path .. mfile
			song.last_duration = 0
			song.typee = split_str[#split_str-1]
			song.index = #songs[song.typee]+1

			local start_time_uf = string.match(mfile, "_%d%d_%d%d_%d%d_%d%d_")
			if start_time_uf then
				local shit = string.Split(string.Trim(start_time_uf, "_"), "_")
				local start_minutes = shit[1]
				local start_seconds = shit[2]
				local end_minutes = shit[3]
				local end_seconds = shit[4]
				song.start = start_minutes * 60 + start_seconds
				song.ending = end_minutes * 60 + end_seconds
			end

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

			if song.typee == "battle" then
				song.typee = "battle_intensive"
				table.insert(songs[song.typee], song)	
			end
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
	songs["suspense"] = {}

	parse_am()
	parse_nombat()
	parse_dynamo("battlemusic")
	parse_dynamo("ayykyu_dynmus")

	shuffle_chosen_songs()

	amready = true
end

concommand.Add("cl_am_verify_songs", function() 
	local failed = {}

	for key, content in pairs(songs) do
		for _, song in ipairs(content) do
			sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
				local split_str = string.Split(song.path, "/")
				local name = string.StripExtension(split_str[#split_str])
	
				if error_code or error_string then
					print("---------------")
					print(song.path.." | "..error_code.." | "..error_string)
					print("---------------")
				end

				if station then
					station:Stop()
				end
			end)
		end
	end
end)


local function fade_channel(channel, to)
	if not am_enabled_global:GetBool() then return end
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
	if not am_enabled_global:GetBool() then return end
	if not amready then return end
	if channel_locked then return end
	if typee == "suspense" and chosen_songs[typee] == nil or chosen_songs[typee] == NULL then
		//print("no suspense songs, switching to battle")
		typee = "battle"
	end
	if not am_enabled[typee]:GetBool() then
		if typee == "background" then
			return
		end

		if typee == "battle" and am_enabled["background"]:GetBool() then 
			typee = "background"
		end
		if typee == "battle" and not am_enabled["background"]:GetBool() then 
			return
		end

		if typee == "battle_intensive" and am_enabled["battle"]:GetBool() then 
			typee = "battle"
		end
		if typee == "battle_intensive" and not am_enabled["battle"]:GetBool() then
			typee = "background" 
		end

		if typee == "suspense" and am_enabled["battle"]:GetBool() then
			typee = "battle"
		end
		if typee == "suspense" and not am_enabled["battle"]:GetBool() then
			typee = "background" 
		end
	end
	if force_type:GetInt() == 1 then typee = "background" end
	if force_type:GetInt() == 2 then typee = "battle" end
	if force_type:GetInt() == 3 then typee = "battle_intensive" end
	if force_type:GetInt() == 4 then typee = "suspense" end
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

		if IsValid(am_current_channel) and am_current_song and am_current_song.typee and am_current_song.index then
			past_channel = am_current_channel
			songs[am_current_song.typee][am_current_song.index].last_duration = past_channel:GetTime()
			fade_channel(past_channel, 0)
		end

		am_current_song = song

		if not am_enabled[typee]:GetBool() then
			channel_locked = false
			return 
		end

		sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
			channel_locked = false
			local split_str = string.Split(song.path, "/")
			local name = string.StripExtension(split_str[#split_str])

			if type_song:GetBool() then
				local matched = string.match(name, "_%d%d_%d%d_%d%d_%d%d_")
				if matched then
					name = string.Replace(name, matched, "")
				end
				chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), "Now playing: ", name)
			end

			if not station then 
				chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 50, 50), "Failed playing: ", name, "\n\t\t\tError Code: ", error_code, "\n\t\t\tError: ", error_string, "\n\t\t\tUsually any error can be resolved by making sure your title has no unicode characters. If you can't find any, simplify it.")
				return 
			end

			am_current_channel = station

			if continue_songs:GetBool() then am_current_channel:SetTime(song.last_duration, true) end
			if am_current_song.start != nil then am_current_channel:SetTime(am_current_song.start, true) end

			am_current_channel:SetVolume(0)
			fade_channel(am_current_channel, volume_scale[typee]:GetFloat())
		end)
	end)

	last_type = typee
end


net.Receive("am_threat_event", function()
	if not am_enabled_global:GetBool() then return end
	if not amready then return end

	local is_targeted = net.ReadBool()
	local hidden = net.ReadBool()
	local boss_fight = net.ReadBool()
	local should_stop = net.ReadBool()

	if should_stop then
		if IsValid(am_current_channel) then
			past_channel = am_current_channel
			songs[am_current_song.typee][am_current_song.index].last_duration = past_channel:GetTime()
			fade_channel(past_channel, 0)
		end
		return
	end

	if is_targeted then
		if hidden then 
			am_play("suspense", 0, false)
		else
			if boss_fight then 
				am_play("battle_intensive", 0, false)
			else
				am_play("battle", 0, false)
			end
		end
	else
		am_play("background", 2, false)
	end

end)

hook.Add("Think", "am_think", function()
	if not am_enabled_global:GetBool() then return end
	if not amready then return end
	if not am_current_song then return end
	if engine.TickCount() % 20 != 0 then return end

	local state = 0
	if IsValid(am_current_channel) then state = am_current_channel:GetState() end

	if LocalPlayer():Health() <= 0 then return end 

	if state == 0 or (IsValid(am_current_channel) and am_current_song.ending != nil and am_current_channel:GetTime() >= am_current_song.ending) then
		am_current_song.last_duration = 0
		chosen_songs[am_current_song.typee] = songs[am_current_song.typee][math.random(#songs[am_current_song.typee])]
		am_play(am_current_song.typee, 0, true)
	end
end)

hook.Add("Think", "am_think_forget", function()
	if not am_enabled_global:GetBool() then return end
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
	if not am_enabled_global:GetBool() then return end
	if not amready then return end

	shuffle_chosen_songs()
	chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), "Reshuffled!")

	if not IsValid(am_current_channel) then return end
	am_current_channel:Stop()
end)