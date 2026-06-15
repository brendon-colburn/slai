using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using MegaCrit.Sts2.Core.Saves;
using MegaCrit.Sts2.Core.Saves.Managers;

namespace SLAI;

public static partial class McpMod
{
    private static void HandleGetProfile(HttpListenerResponse response)
    {
        try
        {
            var dataTask = RunOnMainThread(BuildProfile);
            SendJson(response, dataTask.GetAwaiter().GetResult());
        }
        catch (Exception ex)
        {
            SendError(response, 500, $"Failed to build profile: {ex.Message}");
        }
    }

    private static void HandleGetProfiles(HttpListenerResponse response)
    {
        try
        {
            var dataTask = RunOnMainThread(BuildProfilesSummary);
            SendJson(response, dataTask.GetAwaiter().GetResult());
        }
        catch (Exception ex)
        {
            SendError(response, 500, $"Failed to get profiles: {ex.Message}");
        }
    }

    private static Dictionary<string, object?> BuildProfilesSummary()
    {
        var sm = SaveManager.Instance;
        if (sm == null)
            return Error("Save manager is not available");

        var profiles = new List<Dictionary<string, object?>>();
        for (int i = 1; i <= 3; i++)
        {
            var profileData = new Dictionary<string, object?>
            {
                ["id"] = i,
                ["is_current"] = i == sm.CurrentProfileId,
            };

            try
            {
                var path = ProgressSaveManager.GetProgressPathForProfile(i);
                var resolvedPath = ResolveProfileProgressPath(i);
                profileData["has_data"] = resolvedPath != null && File.Exists(resolvedPath);
                profileData["path"] = path;
                profileData["resolved_path"] = resolvedPath;
            }
            catch
            {
                profileData["has_data"] = false;
            }

            profiles.Add(profileData);
        }

        return new Dictionary<string, object?>
        {
            ["current_profile_id"] = sm.CurrentProfileId,
            ["profiles"] = profiles
        };
    }

    internal static object BuildProfile()
    {
        var progress = SaveManager.Instance?.Progress;
        if (progress == null)
            return new Dictionary<string, object?> { ["error"] = "No profile data available." };

        var result = new Dictionary<string, object?>();

        var characters = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.CharacterStats)
        {
            var stats = kv.Value;
            characters.Add(new Dictionary<string, object?>
            {
                ["id"] = kv.Key.Entry,
                ["max_ascension"] = stats.MaxAscension,
                ["preferred_ascension"] = stats.PreferredAscension,
                ["total_wins"] = stats.TotalWins,
                ["total_losses"] = stats.TotalLosses,
                ["fastest_win_time"] = stats.FastestWinTime,
                ["best_win_streak"] = stats.BestWinStreak,
                ["current_win_streak"] = stats.CurrentWinStreak,
                ["playtime"] = stats.Playtime
            });
        }
        result["characters"] = characters;

        var cards = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.CardStats)
        {
            var stats = kv.Value;
            cards.Add(new Dictionary<string, object?>
            {
                ["id"] = kv.Key.Entry,
                ["times_picked"] = stats.TimesPicked,
                ["times_skipped"] = stats.TimesSkipped,
                ["times_won"] = stats.TimesWon,
                ["times_lost"] = stats.TimesLost
            });
        }
        result["card_stats"] = cards;

        var encounters = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.EncounterStats)
        {
            var enc = new Dictionary<string, object?>
            {
                ["id"] = kv.Key.Entry,
                ["total_wins"] = kv.Value.TotalWins,
                ["total_losses"] = kv.Value.TotalLosses
            };
            var fightStats = new List<Dictionary<string, object?>>();
            foreach (var fs in kv.Value.FightStats)
            {
                fightStats.Add(new Dictionary<string, object?>
                {
                    ["character"] = fs.Character.Entry,
                    ["wins"] = fs.Wins,
                    ["losses"] = fs.Losses
                });
            }
            if (fightStats.Count > 0)
                enc["by_character"] = fightStats;
            encounters.Add(enc);
        }
        result["encounter_stats"] = encounters;

        var enemies = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.EnemyStats)
        {
            var enemy = new Dictionary<string, object?>
            {
                ["id"] = kv.Key.Entry,
                ["total_wins"] = kv.Value.TotalWins,
                ["total_losses"] = kv.Value.TotalLosses
            };
            var fightStats = new List<Dictionary<string, object?>>();
            foreach (var fs in kv.Value.FightStats)
            {
                fightStats.Add(new Dictionary<string, object?>
                {
                    ["character"] = fs.Character.Entry,
                    ["wins"] = fs.Wins,
                    ["losses"] = fs.Losses
                });
            }
            if (fightStats.Count > 0)
                enemy["by_character"] = fightStats;
            enemies.Add(enemy);
        }
        result["enemy_stats"] = enemies;

        var ancients = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.AncientStats)
        {
            var anc = new Dictionary<string, object?>
            {
                ["id"] = kv.Key.Entry,
                ["total_visits"] = kv.Value.TotalVisits,
                ["total_wins"] = kv.Value.TotalWins,
                ["total_losses"] = kv.Value.TotalLosses
            };
            var charStats = new List<Dictionary<string, object?>>();
            foreach (var cs in kv.Value.CharStats)
            {
                charStats.Add(new Dictionary<string, object?>
                {
                    ["character"] = cs.Character.Entry,
                    ["wins"] = cs.Wins,
                    ["losses"] = cs.Losses
                });
            }
            if (charStats.Count > 0)
                anc["by_character"] = charStats;
            ancients.Add(anc);
        }
        result["ancient_stats"] = ancients;

        result["discovered_cards"] = progress.DiscoveredCards.Select(id => id.Entry).ToList();
        result["discovered_relics"] = progress.DiscoveredRelics.Select(id => id.Entry).ToList();
        result["discovered_potions"] = progress.DiscoveredPotions.Select(id => id.Entry).ToList();
        result["discovered_events"] = progress.DiscoveredEvents.Select(id => id.Entry).ToList();
        result["discovered_acts"] = progress.DiscoveredActs.Select(id => id.Entry).ToList();

        var achievements = new List<Dictionary<string, object?>>();
        foreach (var kv in progress.UnlockedAchievements)
        {
            achievements.Add(new Dictionary<string, object?>
            {
                ["id"] = kv.Key,
                ["unlocked_at"] = kv.Value
            });
        }
        result["achievements"] = achievements;

        result["epochs"] = progress.Epochs.Select(e => new Dictionary<string, object?>
        {
            ["id"] = e.Id,
            ["state"] = e.State.ToString(),
            ["obtained"] = e.ObtainDate
        }).ToList();

        result["total_playtime"] = progress.TotalPlaytime;
        result["total_unlocks"] = progress.TotalUnlocks;
        result["current_score"] = progress.CurrentScore;
        result["floors_climbed"] = progress.FloorsClimbed;
        result["architect_damage"] = progress.ArchitectDamage;
        result["total_wins"] = progress.Wins;
        result["total_losses"] = progress.Losses;
        result["fastest_victory"] = progress.FastestVictory;
        result["best_win_streak"] = progress.BestWinStreak;
        result["number_of_runs"] = progress.NumberOfRuns;

        return result;
    }
}
