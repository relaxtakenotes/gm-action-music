// dont kill me for this code omgomgomgomgogm

local fade_time = CreateConVar("cl_am_fadetime_mult", "0.5", FCVAR_ARCHIVE, "How fast the music will change.", 0.01, 10)
local continue_songs = CreateConVar("cl_am_continue_songs", "1", FCVAR_ARCHIVE, "Continue songs where we left off.")
local reset_last_duration = CreateConVar("cl_am_reshuffle_period", "60", FCVAR_ARCHIVE, "Shuffle some songs in a given period. (0 is disabled)")
local reset_current_pack = CreateConVar("cl_am_reshuffle_pack_period", "300", FCVAR_ARCHIVE, "Shuffle the packs in a given period. (0 is disabled)")
local force_type = CreateConVar("cl_am_force_type", "0", FCVAR_ARCHIVE, "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle). 4 - Suspense")
local notify = CreateConVar("cl_am_notify", "0", FCVAR_ARCHIVE, "Notifications!")
local am_enabled_global = CreateConVar("cl_am_enabled_global", "1", FCVAR_ARCHIVE, "Obvious!")

local amready = false

am_current_song = nil
am_current_channel = nil
local past_channel = nil
local channel_locked = false

local songs = {}
local chosen_songs = {}


local current_pack = ""
local packs = {}

chosen_songs["battle"] = {}
chosen_songs["battle_intensive"] = {}
chosen_songs["background"] = {}
chosen_songs["suspense"] = {}

local last_type = ""
local timer_name_counter = 0
local last_forget_time = 0
local last_pack_forget_time = 0

cvars.AddChangeCallback("cl_am_enabled_global", function(convar_name, value_old, value_new)
    if tonumber(value_new) == 0 and IsValid(am_current_channel) then
        am_current_channel:Stop()
    end
end)

local am_enabled = {}
local volume_scale = {}

for _, typee in ipairs({"battle", "background", "battle_intensive", "suspense"}) do
    volume_scale[typee] = CreateConVar("cl_am_volume_" .. typee, "1", FCVAR_ARCHIVE, "Volume. Epic.")
    am_enabled[typee] = CreateConVar("cl_am_enabled_" .. typee, "1", FCVAR_ARCHIVE, "Obvious!")

    cvars.AddChangeCallback("cl_am_volume_" .. typee, function(convar_name, value_old, value_new)
        if tonumber(value_new) < 0.01 then
            print("Use cl_am_enabled for that.")
            volume_scale[typee]:SetFloat(tonumber(value_old))

            return
        end

        if not am_current_song then return end

        if am_current_song.typee == typee then
            am_current_channel:SetVolume(tonumber(value_new))
        end
    end)

    cvars.AddChangeCallback("cl_am_enabled_" .. typee, function(convar_name, value_old, value_new)
        if not am_current_song then return end

        if am_current_song.typee == typee and tonumber(value_new) == 0 and IsValid(am_current_channel) then
            am_current_channel:Stop()
        end
    end)
end

local stroffset = 0

local function screen_text(text)
    stroffset = stroffset + 0.02
    debugoverlay.ScreenText(0.05, 0.6 + stroffset, text, FrameTime(), Color(255, 231, 152))
end

local function get_true_keys(tbl)
    local hold = {}
    for key, state in pairs(tbl) do
        if not state then continue end
        table.insert(hold, key)
    end
    return hold
end

local function find_addon_name_local(path)
    local addon_name = "Unknown"

    local files, dirs = file.Find("addons/*", "GAME")

    for _, dir in ipairs(dirs) do
        if file.Exists("addons/" .. dir .. "/" ..path, "GAME") then
            addon_name = dir
            break
        end
    end

    return addon_name
end

local function categorize_song_path(song)
    local pack_name = "Unknown"

    for _, addon in pairs(engine.GetAddons()) do
        if not addon or not addon.title or not addon.wsid or not addon.mounted or not addon.downloaded then continue end

        if file.Exists(song.path, addon.title) then
            pack_name = addon.title
            break
        end
    end

    if pack_name == "Unknown" then pack_name = find_addon_name_local(song.path) end

    if not songs[song.typee][pack_name] then
        songs[song.typee][pack_name] = {}
    end

    packs[pack_name] = true

    return pack_name
end

local function parse_am()
    for i, search_path in ipairs({"sound/am_music/battle/", "sound/am_music/battle_intensive/", "sound/am_music/background/", "sound/am_music/suspense/"}) do
        local files, _ = file.Find(search_path .. "*", "GAME")
        local split_str = string.Split(search_path, "/")

        for i, mfile in ipairs(files) do
            local song = {}
            song.path = search_path .. mfile
            song.last_duration = 0
            song.typee = split_str[#split_str - 1]
            local pack_category = categorize_song_path(song)
            song.index = #songs[song.typee][pack_category] + 1
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

            table.insert(songs[song.typee][pack_category], song)
        end
    end
end

local function parse_nombat()
    local _, directories = file.Find("sound/nombat/*", "GAME")

    for i, directory in ipairs(directories) do
        local files, _ = file.Find("sound/nombat/" .. directory .. "/*", "GAME")

        for j, mfile in ipairs(files) do
            local song = {}
            song.path = "sound/nombat/" .. directory .. "/" .. mfile
            song.last_duration = 0

            if string.StartWith(mfile, "c") then
                song.typee = "battle"
            else
                song.typee = "background"
            end

            local pack_category = categorize_song_path(song)
            song.index = #songs[song.typee][pack_category] + 1
            table.insert(songs[song.typee][pack_category], song)

            if song.typee == "battle" then
                local song_copy = table.Copy(song)
                song_copy.typee = "battle_intensive"
                table.insert(songs[song_copy.typee][categorize_song_path(song_copy)], song_copy)
            end
        end
    end
end

local function parse_dynamo(dirr)
    for i, search_path in ipairs({"sound/" .. dirr .. "/ambient/", "sound/" .. dirr .. "/combat/bosses/", "sound/" .. dirr .. "/combat/cops/", "sound/" .. dirr .. "/combat/soldiers/", "sound/" .. dirr .. "/combat/aliens/"}) do
        local files, _ = file.Find(search_path .. "*", "GAME")

        for i, mfile in ipairs(files) do
            local song = {}
            song.path = search_path .. mfile
            song.last_duration = 0
            local split_str = string.Split(search_path, "/")
            song.typee = split_str[#split_str - 1]

            if song.typee == "ambient" then
                song.typee = "background"
            end

            if song.typee == "bosses" then
                song.typee = "battle_intensive"
            end

            if song.typee == "aliens" then continue end -- these are not good

            if song.typee == "cops" then
                song.typee = "battle"
            end

            if song.typee == "soldiers" then
                song.typee = "battle"
            end

            local pack_category = categorize_song_path(song)
            song.index = #songs[song.typee][pack_category] + 1

            table.insert(songs[song.typee][pack_category], song)
        end
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

    if file.Exists("am_packs.json", "DATA") then
        local saved_packs = util.JSONToTable(file.Read("am_packs.json", "DATA"))
        if saved_packs then
            for packname, saved_state in pairs(saved_packs) do
                if packs[packname] then packs[packname] = saved_state end
            end
        end
    end

    current_pack = table.Random(get_true_keys(packs))
    for key, item in pairs(chosen_songs) do
        if not songs[key] or not songs[key][current_pack] then continue end
        chosen_songs[key] = songs[key][current_pack][math.random(#songs[key][current_pack])]
    end

    amready = true
end

concommand.Add("cl_am_verify_songs", function()
    for key, content in pairs(songs) do
        for _, song in ipairs(content) do
            sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
                if error_code or error_string then
                    print("---------------")
                    print(song.path .. " | " .. error_code .. " | " .. error_string)
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
    local timer_name = "fade_timer" .. timer_name_counter

    timer.Create(timer_name, 0, math.huge, function()
        if not IsValid(channel) then return end
        lerp_t = math.min(1, lerp_t + fade_time:GetFloat() * FrameTime())
        channel:SetVolume(Lerp(lerp_t, from, to))

        if lerp_t == 1 then
            if to == 0 then
                channel:Stop()
            end

            timer.Remove(timer_name)
        end
    end)
end

local function am_spaghetti_stop()
    if IsValid(am_current_channel) and am_current_song and am_current_song.typee and am_current_song.index then
        pcall(function()
            am_current_song.last_duration = am_current_channel:GetTime()
            songs[am_current_song.typee][current_pack][am_current_song.index].last_duration = am_current_channel:GetTime()
        end)

        pcall(function()
            past_channel = am_current_channel
            fade_channel(past_channel, 0)
        end)

        am_current_song = nil
    end
end

local last_message = "" -- to prevent needless spamming

local function am_notify(message)
    if not notify:GetBool() then return end
    if message == last_message then return end
    chat.AddText(Color(50, 50, 255), "[Action Music] ", Color(255, 255, 255), message)
end

local force_type_array = {"background", "battle", "battle_intensive", "suspense"}

local function am_play(typee, delay, force)
    if not am_enabled_global:GetBool() then return end
    if not amready then return end
    if channel_locked then return end

    if force_type:GetInt() > 0 then
        typee = force_type_array[force_type:GetInt()]
    end

    if typee == "suspense" and not chosen_songs["suspense"] then
        typee = "battle"
    end

    if not am_enabled[typee]:GetBool() then
        if typee == "background" then
            am_spaghetti_stop()

            return
        end

        if typee == "battle" and am_enabled["background"]:GetBool() then
            typee = "background"
        end

        if typee == "battle" and not am_enabled["background"]:GetBool() then
            am_spaghetti_stop()

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

    if chosen_songs[typee] == nil or chosen_songs[typee] == NULL then
        am_notify("There are no songs of type " .. typee .. ". Please include something in it!")

        return
    end

    channel_locked = true

    pcall(function()
        am_current_song.last_duration = am_current_channel:GetTime()
        songs[am_current_song.typee][current_pack][am_current_song.index].last_duration = am_current_channel:GetTime()
    end)

    timer.Simple(delay, function()
        local song = chosen_songs[typee]

        if not continue_songs:GetBool() then
            song = songs[typee][math.random(#songs[typee])]
        end

        if song == nil then
            channel_locked = false

            return
        end

        if am_current_song and am_current_song.path == song.path then
            channel_locked = false

            return
        end

        am_spaghetti_stop()
        am_current_song = song

        if not am_enabled[typee]:GetBool() then
            channel_locked = false

            return
        end

        sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
            channel_locked = false
            local split_str = string.Split(song.path, "/")
            local name = string.StripExtension(split_str[#split_str])
            local matched = string.match(name, "_%d%d_%d%d_%d%d_%d%d_")

            if matched then
                name = string.Replace(name, matched, "")
            end

            am_notify("Now playing: " .. name)

            if not station then
                am_notify("Failed to play: " .. name .. "\n\t\t\tError Code: " .. error_code .. "\n\t\t\tError: " .. error_string .. "\n\t\t\tUsually any error can be resolved by making sure your title has no unicode characters. If you can't find any, simplify it.")

                return
            end

            am_current_channel = station

            if continue_songs:GetBool() then
                am_current_channel:SetTime(song.last_duration, true)
            end

            pcall(function()
                if am_current_song != nil and am_current_song.start != nil then
                    am_current_channel:SetTime(am_current_song.start, true)
                end
            end)

            am_current_channel:SetVolume(0)
            fade_channel(am_current_channel, volume_scale[typee]:GetFloat())
        end)
    end)
end

cvars.AddChangeCallback(force_type:GetName(), function()
    if not am_enabled_global:GetBool() then return end
    if not amready then return end
    last_type = nil -- let the networked stuff take over when we're done
    am_spaghetti_stop()
    if force_type:GetInt() <= 0 then return end
    local typee = force_type_array[force_type:GetInt()]
    am_play(typee, 0, false)
end)

net.Receive("am_threat_event", function()
    if not am_enabled_global:GetBool() then return end
    if not amready then return end
    local is_targeted = net.ReadBool()
    local hidden = net.ReadBool()
    local boss_fight = net.ReadBool()
    local should_stop = net.ReadBool()

    if should_stop then
        last_type = nil
        am_spaghetti_stop()

        return
    end

    if is_targeted then
        if hidden then
            typee = "suspense"
        else
            if boss_fight then
                typee = "battle_intensive"
            else
                typee = "battle"
            end
        end
    else
        typee = "background"
    end

    if last_type == typee then return end
    last_type = typee
    am_play(typee, 0, false)
end)

hook.Add("Think", "am_think", function()
    if GetConVar("developer"):GetBool() and am_current_song then
        screen_text(
            table.ToString(am_current_song, "am_current_song", true)
        )
        screen_text(tostring(am_current_channel))
        screen_text("channel_locked: "..tostring(channel_locked))
        if chosen_songs["battle"] then
            screen_text("battle :"..table.ToString(chosen_songs["battle"]))
        end
        if chosen_songs["battle_intensive"] then
            screen_text("battle_intensive :"..table.ToString(chosen_songs["battle_intensive"]))
        end
        if chosen_songs["background"] then
            screen_text("background :"..table.ToString(chosen_songs["background"]))
        end
        if chosen_songs["suspense"] then
           screen_text("suspense :"..table.ToString(chosen_songs["suspense"]))
        end
        screen_text("current_pack :"..current_pack)
        screen_text(table.ToString(packs, "packs", true))
        stroffset = 0
    end

    if not am_enabled_global:GetBool() then return end
    if not amready then return end
    if not am_current_song then return end
    if engine.TickCount() % 20 ~= 0 then return end
    local state = 0

    if IsValid(am_current_channel) then
        state = am_current_channel:GetState()
    end

    if state == 0 or (IsValid(am_current_channel) and am_current_song.ending ~= nil and am_current_channel:GetTime() >= am_current_song.ending) then
        if state != 0 then
            am_current_song.last_duration = 0
        end
        chosen_songs[am_current_song.typee] = songs[am_current_song.typee][current_pack][math.random(#songs[am_current_song.typee][current_pack])]

        if LocalPlayer():Health() > 0 then
            am_play(am_current_song.typee, 0, true)
        end
    end

end)

hook.Add("Think", "am_think_forget", function()
    if not am_enabled_global:GetBool() then return end

    if reset_current_pack:GetBool() then
        if CurTime() - last_pack_forget_time > reset_current_pack:GetInt() then
            last_pack_forget_time = CurTime()

            current_pack = table.Random(get_true_keys(packs))
        end
    end

    if reset_last_duration:GetBool() then
        if CurTime() - last_forget_time > reset_last_duration:GetInt() then
            last_forget_time = CurTime()

            for key, item in pairs(chosen_songs) do
                if not songs[key] or not songs[key][current_pack] then continue end
                if am_current_song and am_current_song.typee == key then continue end
                chosen_songs[key] = songs[key][current_pack][math.random(#songs[key][current_pack])]
            end
        end
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

    for key, item in pairs(chosen_songs) do
        if not songs[key] or not songs[key][current_pack] then continue end
        chosen_songs[key] = songs[key][current_pack][math.random(#songs[key][current_pack])]
    end

    am_notify("Reshuffled!")
    if not IsValid(am_current_channel) then return end
    am_current_channel:Stop()
end)

concommand.Add("cl_am_reshuffle_pack", function(ply, cmd, args)
    if not am_enabled_global:GetBool() then return end
    if not amready then return end

    current_pack = table.Random(get_true_keys(packs))

    am_notify("Reshuffled the pack!")
    //if not IsValid(am_current_channel) then return end
    //am_current_channel:Stop()
end)

concommand.Add("cl_am_packs_configure", function(ply, cmd, args)
    local scrw = ScrW()
    local scrh = ScrH()
    local ww = scrw / 4
    local wh = scrh / 2

    local m = 5

    local frame = vgui.Create("DFrame")
    frame:SetTitle("Action Music Packs")
    frame:SetPos(scrw / 2 - ww / 2, scrh / 2 - wh / 2)
    frame:SetSize(ww, wh)
    frame:SetVisible(true)
    frame:SetDraggable(true)
    frame:SetSizable(true)
    frame:ShowCloseButton(true)
    frame:MakePopup()

    local scroll = vgui.Create("DScrollPanel", frame)
    scroll:Dock(FILL)

    for packname, state in pairs(packs) do
        local control = vgui.Create("DButton", scroll)

        local bw = ww - 10
        local bh = 30
        local bpx = bw / 4
        local bpy = bh / 2

        control.DoClick = function()
            packs[packname] = !packs[packname]
            file.Write("am_packs.json", util.TableToJSON(packs))
        end

        local og_paint = control.Paint

        control.Paint = function(self, w, h)
            og_paint(self, w, h)

            if packs[packname] then
                control:SetText("Disable: " .. packname)
            else
                control:SetText("Enable: " .. packname)
            end
        end

        if state then
            control:SetText("Disable: " .. packname)
        else
            control:SetText("Enable: " .. packname)
        end

        control:SetSize(bw, bh)
        control:SetPos(bpx, bpy)
        control:Dock(TOP)
        control:DockMargin(m, m, m, m)
    end
end)

hook.Add("PopulateToolMenu", "am_settings_populate", function()
    spawnmenu.AddToolMenuOption("Options", "am_9999_tool", "am_9999_main", "Main", nil, nil, function(panel)
        panel:ClearControls()

        panel:CheckBox("Enabled", am_enabled_global:GetName())
        panel:CheckBox("Notifications", notify:GetName())
        panel:CheckBox("Continue songs from where we left off", continue_songs:GetName())

        panel:NumSlider("Force Type", force_type:GetName(), 0, 4, 0)
        panel:ControlHelp("0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle). 4 - Suspense.\nDon't spam this unless you want a loud mess.")

        panel:NumSlider("Pack Shuffle Period", reset_current_pack:GetName(), 0, 1000, 0)
        panel:NumSlider("Song Shuffle Period", reset_last_duration:GetName(), 0, 1000, 0)

        panel:NumSlider("Fade Time", fade_time:GetName(), 0.01, 5, 1)

        for _, typee in ipairs({"battle", "background", "battle_intensive", "suspense"}) do
            panel:CheckBox("Enabled (" .. typee .. ")", "cl_am_enabled_" .. typee)
            panel:NumSlider("Volume (" .. typee .. ")", "cl_am_volume_" .. typee, 0, 1, 2)
        end

        panel:Button("Reshuffle Pack", "cl_am_reshuffle_pack")
        panel:Button("Reshuffle Songs", "cl_am_reshuffle")

        panel:Button("Initialize songs (Will Lag!)", "cl_am_initialize_songs")
    end)

    spawnmenu.AddToolMenuOption("Options", "am_9999_tool", "am_9999_packs", "Packs", nil, nil, function(panel)
        panel:ClearControls()

        panel:Button("Open Packs Configuration", "cl_am_packs_configure")
    end)
end)

hook.Add("AddToolMenuCategories", "am_add_category", function()
    spawnmenu.AddToolCategory("Options", "am_9999_tool", "Action Music")
end)