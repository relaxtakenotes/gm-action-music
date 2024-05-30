// dont kill me for this code omgomgomgomgogm

local fade_time = CreateConVar("cl_am_fadetime_mult", "0.5", FCVAR_ARCHIVE, "How fast the music will change.", 0.01, 10)
local continue_songs = CreateConVar("cl_am_continue_songs", "1", FCVAR_ARCHIVE, "Continue songs where we left off.")
local reset_last_duration = CreateConVar("cl_am_reshuffle_period", "60", FCVAR_ARCHIVE, "Shuffle some songs in a given period. (0 is disabled)")
local reset_current_pack = CreateConVar("cl_am_reshuffle_pack_period", "300", FCVAR_ARCHIVE, "Shuffle the packs in a given period. (0 is disabled)")
local force_type = CreateConVar("cl_am_force_type", "0", FCVAR_ARCHIVE, "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle). 4 - Suspense")
local notify = CreateConVar("cl_am_notify", "0", FCVAR_ARCHIVE, "Notifications!")
local enabled = CreateConVar("cl_am_enabled_global", "1", FCVAR_ARCHIVE, "Obvious!")

local songs = {}
local chosen_songs = {}
chosen_songs["battle"] = {}
chosen_songs["battle_intensive"] = {}
chosen_songs["background"] = {}
chosen_songs["suspense"] = {}

local packs = {}
local current_pack = ""

local last_type = ""
local timer_name_counter = 0
local last_forget_time = 0
local last_pack_forget_time = 0

cvars.AddChangeCallback("cl_am_enabled_global", function(convar_name, value_old, value_new)
    if tonumber(value_new) == 0 and IsValid(current_channel) then
        current_channel:Stop()
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

        if not current_song then return end

        if current_song.typee == typee then
            current_channel:SetVolume(tonumber(value_new))
        end
    end)

    cvars.AddChangeCallback("cl_am_enabled_" .. typee, function(convar_name, value_old, value_new)
        if not current_song then return end

        if current_song.typee == typee and tonumber(value_new) == 0 and IsValid(current_channel) then
            current_channel:Stop()
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

local function shuffle_pack()
    current_pack = table.Random(get_true_keys(packs))
end

local function pick_chosen_songs()
    for key, item in pairs(chosen_songs) do
        if not songs[key] or not songs[key][current_pack] then continue end
        chosen_songs[key] = songs[key][current_pack][math.random(#songs[key][current_pack])]
    end
end

local function pick_song(typee)
    return songs[typee][current_pack][math.random(#songs[typee][current_pack])]
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

    shuffle_pack()
    pick_chosen_songs()

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
    if not enabled:GetBool() then return end

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

local function am_spaghetti_stop(target_channel, typee, pack, index)
    if IsValid(target_channel) then
        if typee and pack and index != nil then
            songs[typee][pack][index].last_duration = target_channel:GetTime()
        end

        past_channel = target_channel
        fade_channel(past_channel, 0)
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
    if not enabled:GetBool() then return end

    if not amready then
        print("[am_play] not ready")
        return
    end

    //if not IsValid(current_channel) then channel_locked = false end

    if channel_locked then
        print("[am_play] channel is locked")
        return
    end

    if force_type:GetInt() > 0 then
        typee = force_type_array[force_type:GetInt()]
    end

    if typee == "suspense" and not chosen_songs["suspense"] then
        typee = "battle"
    end

    if not am_enabled[typee]:GetBool() then
        if typee == "background" then
            if current_song then
                am_spaghetti_stop(current_channel, current_song.type, current_pack, current_song.index)
            end
            return
        end

        if typee == "battle" and am_enabled["background"]:GetBool() then
            typee = "background"
        end

        if typee == "battle" and not am_enabled["background"]:GetBool() then
            if current_song then
                am_spaghetti_stop(current_channel, current_song.type, current_pack, current_song.index)
            end
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

    if not am_enabled[typee]:GetBool() then
        print("[am_play] not enabled")
        return
    end

    if not IsValid(chosen_songs) or not chosen_songs[typee] then
        pick_chosen_songs()
    end

    local song = chosen_songs[typee]
    if not continue_songs:GetBool() then
        song = pick_song(typee)
    end

    if not song then
        print("[am_play] no song")
        return
    end

    if current_song and current_song.path == song.path then
        print("[am_play] current song path and new song paths match")
        return
    end

    channel_locked = true

    timer.Simple(delay, function()
        sound.PlayFile(song.path, "noblock", function(station, error_code, error_string)
            channel_locked = false

            local split_str = string.Split(song.path, "/")
            local name = string.StripExtension(split_str[#split_str])
            local matched = string.match(name, "_%d%d_%d%d_%d%d_%d%d_")

            if matched then
                name = string.Replace(name, matched, "")
            end

            if not station then
                am_notify("Failed to play: " .. name .. "\n\t\t\tError Code: " .. error_code .. "\n\t\t\tError: " .. error_string .. "\n\t\t\tUsually any error can be resolved by making sure your title has no unicode characters. If you can't find any, simplify it.")
                return
            end

            am_notify("Now playing: " .. name)

            if current_song then
                am_spaghetti_stop(current_channel, current_song.type, current_pack, current_song.index)
            end
            current_song = song
            current_channel = station

            if current_song.start then
                current_channel:SetTime(current_song.start, true)
            end

            if continue_songs:GetBool() then
                current_channel:SetTime(song.last_duration, true)
            end

            current_channel:SetVolume(0)
            fade_channel(current_channel, volume_scale[typee]:GetFloat())
        end)
    end)
end

cvars.AddChangeCallback(force_type:GetName(), function()
    if not enabled:GetBool() then return end
    if not amready then return end

    last_type = nil -- let the networked stuff take over when we're done
    if current_song then
        am_spaghetti_stop(current_channel, current_song.type, current_pack, current_song.index)
    end

    if force_type:GetInt() <= 0 then return end

    local typee = force_type_array[force_type:GetInt()]
    am_play(typee, 0, false)
end)

net.Receive("am_threat_event", function()
    if not enabled:GetBool() then return end
    if not amready then return end
    local is_targeted = net.ReadBool()
    local hidden = net.ReadBool()
    local boss_fight = net.ReadBool()
    local should_stop = net.ReadBool()

    if should_stop then
        last_type = nil
        if current_song then
            am_spaghetti_stop(current_channel, current_song.type, current_pack, current_song.index)
        end
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
    if GetConVar("developer"):GetBool() and current_song then
        screen_text(
            table.ToString(current_song, "current_song", true)
        )
        screen_text(tostring(current_channel))
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

    if not enabled:GetBool() or not amready or not current_song then return end

    if engine.TickCount() % 30 ~= 0 then return end

    local state = 0

    if IsValid(current_channel) then
        state = current_channel:GetState()
    end

    if state == 0 then
        current_song.last_duration = 0

        //pick_chosen_songs()
        //if not current_song or not chosen_songs[current_song.typee] or not songs[current_song.typee] then
        //    return
        //end

        chosen_songs[current_song.typee] = songs[current_song.typee][current_pack][math.random(#songs[current_song.typee][current_pack])]

        if LocalPlayer():Health() > 0 then
            am_play(current_song.typee, 0, true)
        end
    end
end)

hook.Add("Think", "am_think_forget", function()
    if not enabled:GetBool() then return end

    if reset_current_pack:GetBool() then
        if CurTime() - last_pack_forget_time > reset_current_pack:GetInt() then
            last_pack_forget_time = CurTime()
            shuffle_pack()
        end
    end

    if reset_last_duration:GetBool() then
        if CurTime() - last_forget_time > reset_last_duration:GetInt() then
            last_forget_time = CurTime()
            pick_chosen_songs()
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
    if not enabled:GetBool() or not amready then return end

    pick_chosen_songs()

    am_notify("Reshuffled!")
    if not IsValid(current_channel) then return end
    current_channel:Stop()
end)

concommand.Add("cl_am_reshuffle_pack", function(ply, cmd, args)
    if not enabled:GetBool() or not amready then return end

    shuffle_pack()

    am_notify("Reshuffled the pack!")
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

        panel:CheckBox("Enabled", enabled:GetName())
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