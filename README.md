```
A very easy to use Dynamic Action Music mod for Garry's Mod, which is inspired by dynamo and nombat.

Features:
    - Automatic fade-in and fade-out.
    - Ease of use
    - Dynamo/sbm and nombat pack parsing
    - Different types of "actions": battle, intensive battle, background
    - Extensive configuration for advanced users

How to use:
    To start you can use any dynamo, sbm or nombat pack. Keep in mind for dynamo and sbm packs the "alien" category is discarded due to it not fitting into the existing action types.
    Alternatively you can create your own pack by just creating a folder in your addons directory and creating directories as such:
        sound -> am_music -> battle
                          -> battle_intensive
                          -> background
        Then just sort your music accordingly, you usually don't need to edit or convert it in any way, unless you wish to change a specific song to fit better.
        Make sure there are no unicode characters in the filenames inorder to not get stuck on an error. If an error still happens make sure the filename is as concise and short as possible. If even that didn't help your audio file can not be read by GMOD and needs to be converted to something else.

Commands (Don't understand any of these? Don't mess with them. Keep them at default):
    - cl_am_fadetime_mult - How fast the songs will fade-in/fade-out (float)
    - cl_am_continue_songs - Continue songs where we left off (0/1)
    - cl_am_reshuffle_period - Reshuffle songs in a certain given period (seconds)
    - cl_am_force_type - Force a specific action type (0 - disabled, 1 - background, 2 - battle, 3 - intensive battle)
    - cl_am_chat_print - Print music changes to chat (0/1)
    - cl_am_enabled_battle - Toggle (0/1)
    - cl_am_enabled_background - Toggle (0/1)
    - cl_am_enabled_battle_intensive - Toggle (0/1)
    - cl_am_enabled_global - Toggle (0/1)
    - cl_am_volume_battle - Volume (0-1)
    - cl_am_volume_background - Volume (0-1)
    - cl_am_volume_battle_intensive - Volume (0-1)
    - sv_am_allow_team_trigger - Allow the mod to mark the player as targeted if close friendly npc's are being targeted as well. (0/1)
    - sv_am_allow_alternate_trigger - If the npc is close to you, hates you and is in combat/alert, then mark him as targeting us. (0/1)
    - sv_am_enemy_threshold - If there are more than some amount of npc's that are ready to kick your ass, consider this an intense battle. (any number)

How each "action" gets triggered:
    - Background:
        - If there's no one going after you or nothing is going on this will play. Basically ambience.
    - Battle:
        - Obviously from the name this will play if you get targeted by some NPC's.
    - Intensive battle:
        - Gets played if you're targeted by a lot of NPC's or by specific boss ones.
```
