util.AddNetworkString("am_threat_event")

local allow_team_trigger = CreateConVar("sv_am_allow_team_trigger", "1", FCVAR_ARCHIVE, "Allow the mod to mark the player as targeted if close friendly npc's are being targeted as well.")
local allow_alt_trigger = CreateConVar("sv_am_allow_alternate_trigger", "1", FCVAR_ARCHIVE, "If the npc is close to you, hates you and is in combat/alert, then mark him as targeting us.")
local bosses = {"npc_combinegunship", "npc_hunter", "npc_helicopter", "npc_strider"}

local function targeted_teammate_is_near(target, ply)
	if not allow_team_trigger:GetBool() then return false end
	if not target:IsNPC() then return false end
	if target:Disposition(ply) != D_LI then return false end
	if target:GetPos():Distance(ply:GetPos()) > 1250 then return false end

	return true
end

local function enemy_is_alerted_and_close(npc, ply)
	if not allow_alt_trigger:GetBool() then return false end
	if npc:Disposition(ply) != D_HT then return false end
	if npc:GetPos():Distance(ply:GetPos()) > 1250 then return false end 
	if npc:GetNPCState() != NPC_STATE_COMBAT and npc:GetNPCState() != NPC_STATE_ALERT and npc:GetActivity() != ACT_COMBAT_IDLE then return false end

	return true
end

hook.Add("FinishMove", "am_threat_loop", function(ply, mv)
	local is_targeted = false
	local by_npc = nil
	local boss = nil

	ply.is_targeted = is_targeted
	ply.by_npc = by_npc

	if ply.am_timeout and ply.am_timeout > 0 then
		ply.am_timeout = math.max(ply.am_timeout - FrameTime(), 0) 
		return 
	end

	ply.am_timeout = 1

	for _, npc in ipairs( ents.FindByClass( "npc_*" ) ) do
		if not IsValid(npc) or not npc:IsNPC() or not npc.GetEnemy then continue end
		local target = npc:GetEnemy()

		// if target is valid and it's us. then we are targeted by some npc
		// or if we can trigger by team then if the friendly npc close to us is getting targeted then we get targeted as well
		if IsValid(target) and (target == ply or targeted_teammate_is_near(target, ply)) then
			is_targeted = true
			by_npc = npc
		end

		// if we arent targeted but there are enemy npc's nearby that are in combat/alert then count us as targeted
		if not is_targeted and enemy_is_alerted_and_close(npc, ply) then
			is_targeted = true
			by_npc = npc
		end

		// if we are targeted and there's a boss nearby, prioritize being targeted by the boss for epic music
		if is_targeted and table.HasValue(bosses, npc:GetClass()) then
			boss = npc
		end
	end

	net.Start("am_threat_event", true)
	net.WriteBool(is_targeted)
	if IsValid(boss) then net.WriteEntity(boss) else net.WriteEntity(by_npc) end
	net.Send(ply)
end)
