util.AddNetworkString("am_threat_event")
local allow_team_trigger = CreateConVar("sv_am_allow_team_trigger", "1", FCVAR_ARCHIVE, "Allow the mod to mark the player as targeted if close friendly npc's are being targeted as well.")
local allow_alt_trigger = CreateConVar("sv_am_allow_alternate_trigger", "1", FCVAR_ARCHIVE, "If the npc is close to you, hates you and is in combat/alert, then mark him as targeting us.")
local enemy_threshold = CreateConVar("sv_am_enemy_threshold", "8", FCVAR_ARCHIVE, "If there are more than some amount of npc's that are ready to kick your ass, consider this an intense battle.")
local allow_pvp = CreateConVar("sv_am_allow_pvp_trigger", "1", FCVAR_ARCHIVE, "Allow a hacky method to detect PVP situations to affect the threat system")
local pvp_time = CreateConVar("sv_am_pvp_time", "45", FCVAR_ARCHIVE, "For how long to consider a player being in a battle after being shot at.")
local suspense = CreateConVar("sv_am_send_suspense", "1", FCVAR_ARCHIVE, "Allow clients to use the suspense state")
local hidden_time = CreateConVar("sv_am_hidden_time", "25", FCVAR_ARCHIVE, "After how long to consider a player hidden once he's out of enemy visibility.")
local targeted_time = CreateConVar("sv_am_targeted_timer", "5", FCVAR_ARCHIVE, "How fast to switch off from the targeted state.")
local expensive_vis = CreateConVar("sv_am_expensive_hidden_checks", "0", FCVAR_ARCHIVE, "Run a shitton of vischecks to determine the hidden state.")
local ignore_noncombatans = CreateConVar("sv_am_ignore_noncombatans", "1", FCVAR_ARCHIVE, "Ignore NPC's that are hostile to you in some way but don't have a weapon.")

local bosses = {"npc_combinegunship", "npc_hunter", "npc_helicopter", "npc_strider", "a_shit_ton_of_enemies"}

local ignore_list = {"npc_clawscanner", "npc_stalker", "npc_turret_floor", "npc_combinedropship", "npc_cscanner", "npc_turret_ceiling", "npc_combine_camera", "npc_crow", "npc_pigeon", "npc_seagull"}

local recent_shots = {}

local function targeted_teammate_is_near(target, ply)
    if not allow_team_trigger:GetBool() then return false end
    if not target:IsNPC() then return false end
    if target:Disposition(ply) ~= D_LI then return false end
    if target:GetPos():Distance(ply:GetPos()) > 1250 and not target.am_teammate_was_close then return false end
    target.am_teammate_was_close = true

    return true
end

local function enemy_is_alerted_and_close(npc, ply)
    if not allow_alt_trigger:GetBool() then return false end
    if npc:Disposition(ply) ~= D_HT then return false end
    if npc:GetPos():Distance(ply:GetPos()) > 1250 and not npc.am_alerted_was_close then return false end
    if npc:GetNPCState() ~= NPC_STATE_COMBAT and npc:GetNPCState() ~= NPC_STATE_ALERT and npc:GetActivity() ~= ACT_COMBAT_IDLE then return false end
    npc.am_alerted_was_close = true

    return true
end

local stroffset = 0

local function screen_text(text)
    stroffset = stroffset + 0.02
    debugoverlay.ScreenText(0.05, 0.1 + stroffset, text, 1 + engine.TickInterval() * 4, Color(156, 219, 255))
end

local function npc_can_attack(npc)
    if not ignore_noncombatans:GetBool() then return true end
    if not isfunction(npc.GetActiveWeapon) or npc:GetActiveWeapon() ~= NULL then return true end
    if npc:GetShootPos():Distance(npc:GetPos()) > 0 and bit.band(npc:CapabilitiesGet(), CAP_USE_WEAPONS) == CAP_USE_WEAPONS then return false end

    return true
end

local function get_entity_points(ent)
    local points = {}
    local maxs = ent:OBBMaxs()
    local mins = ent:OBBMins()
    local origin = ent:GetPos()
    table.insert(points, origin + Vector(mins.x, mins.y, mins.z))
    table.insert(points, origin + Vector(maxs.x, mins.y, mins.z))
    table.insert(points, origin + Vector(mins.x, maxs.y, mins.z))
    table.insert(points, origin + Vector(mins.x, mins.y, maxs.z))
    table.insert(points, origin + Vector(maxs.x, maxs.y, mins.z))
    table.insert(points, origin + Vector(maxs.x, mins.y, maxs.z))
    table.insert(points, origin + Vector(mins.x, maxs.y, maxs.z))
    table.insert(points, origin + Vector(maxs.x, maxs.y, maxs.z))
    table.insert(points, origin + ent:OBBCenter())

    return points
end

local function entities_see_each_other(ent1, ent2)
    if not suspense:GetBool() then return true end

    local tr = util.TraceLine({
        start = ent1:GetShootPos(),
        endpos = ent2:GetShootPos(),
        filter = {ent1, ent2},
        mask = MASK_VISIBLE_AND_NPCS
    })

    if tr.Fraction >= 0.99 then return true end
    if not expensive_vis:GetBool() then return false end
    local ent1_points = get_entity_points(ent1)
    local ent2_points = get_entity_points(ent2)

    for i, point in ipairs(ent2_points) do
        local tr = util.TraceLine({
            start = ent1:GetShootPos(),
            endpos = point,
            filter = {ent1, ent2},
            mask = MASK_VISIBLE_AND_NPCS
        })

        if tr.Fraction >= 0.99 then return true end
    end

    for i, point in ipairs(ent1_points) do
        local tr = util.TraceLine({
            start = ent2:GetShootPos(),
            endpos = point,
            filter = {ent1, ent2},
            mask = MASK_VISIBLE_AND_NPCS
        })

        if tr.Fraction >= 0.99 then return true end
    end

    return false
end

hook.Add("FinishMove", "am_threat_loop", function(ply, mv)
    if engine.TickCount() % 2 == 0 then return end

    if ply.am_timeout and ply.am_timeout > 0 then
        ply.am_timeout = math.max(ply.am_timeout - FrameTime() * 2, 0) -- frametime*2 cuz we're skipping half the ticks

        return
    end

    ply.am_timeout = 1
    ply.am_active_enemies = {}
    ply.am_is_targeted_prev = ply.am_is_targeted
    ply.am_hidden_prev = ply.am_hidden
    ply.am_boss_fight_prev = ply.am_boss_fight
    --ply.am_is_targeted = false // this will be changed later
    ply.am_hidden = false
    --ply.am_boss_fight = false // this will be changed later
    ply.am_enemy_amount = 0
    ply.am_hidden_from_enemies = 0
    ply.am_should_stop_prev = ply.am_should_stop
    ply.am_should_stop = false
    local ignore_bossfight_flag = false
    local overall_enemy_count = 0

    for _, npc in ipairs(ents.FindByClass("npc_*")) do
        if table.HasValue(ignore_list, npc:GetClass()) then continue end
        if not IsValid(npc) or not npc:IsNPC() or not npc.GetEnemy then continue end --print(IsValid(npc), npc:IsNPC(), npc.GetEnemy, " --- ", npc)
        local target = npc:GetEnemy()
        if not target or not target:IsValid() then continue end
        if not npc_can_attack(npc) then continue end
        overall_enemy_count = overall_enemy_count + 1

        if target == ply or targeted_teammate_is_near(target, ply) or enemy_is_alerted_and_close(npc, ply) then
            ply.am_active_enemies[npc] = true
        end
    end

    for i, data in ipairs(recent_shots) do
        data.time = data.time - 1

        if data.time <= 0 or data.entity:Health() <= 0 then
            table.remove(recent_shots, i)
            continue
        end

        if data.entity == ply or data.ignore[ply] then continue end

        if data.entity:GetPos():Distance(ply:GetPos()) > data.distance * 3 then
            data.ignore[ply] = true
            continue
        end

        if data.targeted[ply] then
            ply.am_active_enemies[data.entity] = true
        end
    end

    for enemy, _ in pairs(ply.am_active_enemies) do
        ply.am_enemy_amount = (ply.am_enemy_amount or 0) + 1

        if table.HasValue(bosses, enemy:GetClass()) then
            ply.am_boss_fight = true
            ignore_bossfight_flag = true
        end

        if not entities_see_each_other(enemy, ply) then
            ply.am_hidden_from_enemies = ply.am_hidden_from_enemies + 1
        end
    end

    if ply.am_enemy_amount > 0 then
        ply.am_is_targeted = true
    elseif ply.am_is_targeted then
        ply.am_targeted_timer = (ply.am_targeted_timer or 0) + ply.am_timeout
        local mult = 1

        if overall_enemy_count <= 0 then
            mult = 0.2
        end

        if ply.am_targeted_timer > targeted_time:GetFloat() * mult then
            ply.am_is_targeted = false
            ply.am_boss_fight = false
            ply.am_targeted_timer = 0
        end
    end

    if ply.am_enemy_amount > enemy_threshold:GetInt() and not ignore_bossfight_flag then
        ply.am_boss_fight = true
    end

    if ply.am_enemy_amount <= ply.am_hidden_from_enemies and ply.am_enemy_amount > 0 then
        ply.am_hidden_timer = (ply.am_hidden_timer or 0) + ply.am_timeout
    else
        ply.am_hidden_timer = 0
    end

    ply.am_hidden = ply.am_hidden_timer > hidden_time:GetFloat()
    ply.am_should_stop = ply:Health() <= 0

    if ply.am_should_stop then
        ply.am_is_targeted = false
        ply.am_boss_fight = false
        ply.am_targeted_timer = 0
    end

    if GetConVar("developer"):GetBool() then
        screen_text("am_timeout: "..tostring(ply.am_timeout))
        screen_text("am_active_enemies: "..table.ToString(ply.am_active_enemies))
        screen_text("am_is_targeted_prev: "..tostring(ply.am_is_targeted_prev))
        screen_text("am_hidden_prev: "..tostring(ply.am_hidden_prev))
        screen_text("am_boss_fight_prev: "..tostring(ply.am_boss_fight_prev))
        screen_text("am_hidden: "..tostring(ply.am_hidden))
        screen_text("am_enemy_amount: "..tostring(ply.am_enemy_amount))
        screen_text("am_hidden_from_enemies: "..tostring(ply.am_hidden_from_enemies))
        screen_text("am_should_stop_prev: "..tostring(ply.am_should_stop_prev))
        screen_text("am_should_stop: "..tostring(ply.am_should_stop))
        stroffset = 0
    end
    
    net.Start("am_threat_event", false)
    net.WriteBool(ply.am_is_targeted)
    net.WriteBool(ply.am_hidden)
    net.WriteBool(ply.am_boss_fight)
    net.WriteBool(ply.am_should_stop)
    net.Send(ply)
end)

hook.Add("EntityFireBullets", "am_detect_action", function(attacker, data)
    if not allow_pvp:GetBool() then return end
    local entity = NULL
    local weapon = NULL

    if attacker:IsPlayer() or attacker:IsNPC() then
        entity = attacker
        weapon = entity:GetActiveWeapon()
    else
        weapon = attacker
        entity = weapon:GetOwner()

        if entity == NULL then
            entity = attacker
            weaponIsWeird = true
        end
    end

    if not entity:IsPlayer() then return end -- WE DO NOT CARE

    -- todo: make a library to detect shots and use it instead
    local tr = util.TraceLine({
        start = data.Src,
        endpos = data.Src + data.Dir * 100000,
        filter = entity
    })

    local f_targetted = {}

    for _, ent in ipairs(ents.FindInBox(tr.HitPos - Vector(200, 200, 200), tr.HitPos + Vector(200, 200, 200))) do
        f_targetted[ent] = true
    end

    table.insert(recent_shots, {
        pos = tr.HitPos,
        distance = tr.HitPos:Distance(data.Src),
        time = pvp_time:GetFloat(),
        entity = entity,
        ignore = {},
        targeted = f_targetted
    })
end)

concommand.Add("sv_am_ambient_enable", function(ply, cmd, args)
    for i, ent in ipairs(ents.GetAll()) do
        if not IsValid(ent) then continue end
        if ent:GetClass() ~= "ambient_generic" then continue end
        ent:SetKeyValue("health", "10")
    end
end)

concommand.Add("sv_am_ambient_disable", function(ply, cmd, args)
    for i, ent in ipairs(ents.GetAll()) do
        if not IsValid(ent) then continue end
        if ent:GetClass() ~= "ambient_generic" then continue end
        ent:SetKeyValue("health", "0")
    end
end)
