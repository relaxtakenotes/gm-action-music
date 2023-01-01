# gm-action-music
 Dynamic Action Music for GMOD. Inspired by DYNAMO and Nombat

## Features:
 - Automatic fade-in and fade-out.
 - Ease of use
 - Dynamo/sbm and nombat pack parsing
 - Different types of "actions": battle, intensive battle, background

## How action types get triggered:
 - Background
   - If there's no one going after you or nothing is going on this will play. Basically ambience.
 - Battle
   - Obviously from the name this will play if you get targeted by some NPC's.
 - Intensive battle
   - Gets played if you're targeted by a lot of NPC's or by specific boss ones.

## Commands:
	sv_am_allow_team_trigger - "Allow the mod to mark the player as targeted if close friendly npc's are being targeted as well."
	sv_am_allow_alternate_trigger - "If the npc is close to you, hates you and is in combat/alert, then mark him as targeting us."
	sv_am_enemy_threshold - "If there are more than some amount of npc's that are ready to kick your ass, consider this an intense battle."
	cl_am_fadetime_mult - "How fast the music will change."
	cl_am_continue_songs - "Continue songs where we left off."
	cl_am_volume - "Volume. Epic."
	cl_am_force_type - "If you got some RP scenario where you want only one type of music playing you can change this. 0 - Disabled. 1 - Background. 2 - Battle. 3 - Intense Battle (Boss Battle)"
	cl_am_chat_print - "Print music change to chat."

## How to use:
 Download the mod, put it into your addons folder and then create your own music pack by creating a folder, creating directories sound->am_music->battle/battle_intensive/background and sorting your music accordingly. You don't need to format them in anyway except removing any unicode symbols from the filename. Alternatively you may download dynamo/sbm and nombat packs, they will be parsed as well. One thing you have to keep in mind is that all different types have to be filled, otherwise your console will be spammed.

## To note:
This is pretty raw in the current state but in the limited testing it had I deem it github-worthy for now.
