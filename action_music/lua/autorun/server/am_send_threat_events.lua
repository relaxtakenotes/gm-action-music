util.AddNetworkString("am_threat_event")

hook.Add("FinishMove", "am_threat_loop", function(ply, mv)
	local is_targeted = false
	local by_npc = NULL

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
		if IsValid(target) and target == ply then
			is_targeted = true
			by_npc = npc
			break
		end 
	end

	net.Start("am_threat_event", true)
	net.WriteBool(is_targeted)
	net.WriteEntity(by_npc)
	net.Send(ply)
end)
