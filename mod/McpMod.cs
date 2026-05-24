// SLAI mod — read-only HTTP observer for Slay the Spire 2.
//
// Forked from STS2MCP (https://github.com/Gennadiyev/STS2MCP, MIT © Yikun Ji).
// This fork keeps STS2MCP's state-observation core (StateBuilder, Helpers,
// Formatting, Compendium, Wiki, Profile) and strips the action endpoints,
// multiplayer surface, and Fast Mode UI. SLAI is a coaching observer only;
// it cannot send game inputs. See LICENSE.STS2MCP for the upstream notice.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Godot;
using MegaCrit.Sts2.Core.Modding;

namespace SLAI;

[ModInitializer("Initialize")]
public static partial class McpMod
{
    public const string Version = "0.1.0";
    public const int DefaultPort = 15526;
    private const string ConfigFileName = "SLAI.conf";

    private static HttpListener? _listener;
    private static Thread? _serverThread;
    private static readonly ConcurrentQueue<Action> _mainThreadQueue = new();
    internal static readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    private static int LoadPort()
    {
        try
        {
            string? modDir = Path.GetDirectoryName(
                System.Reflection.Assembly.GetExecutingAssembly().Location);
            if (modDir == null) return DefaultPort;

            string configPath = Path.Combine(modDir, ConfigFileName);
            if (!File.Exists(configPath))
            {
                try
                {
                    var defaultConfig = new Dictionary<string, object> { ["port"] = DefaultPort };
                    string json = JsonSerializer.Serialize(defaultConfig, _jsonOptions);
                    File.WriteAllText(configPath, json);
                    GD.Print($"[SLAI] Created default config at {configPath}");
                }
                catch (Exception ex) when (ex is UnauthorizedAccessException or IOException)
                {
                    GD.Print($"[SLAI] No config found at {configPath}; using default port {DefaultPort}");
                }
                return DefaultPort;
            }

            string content = File.ReadAllText(configPath);
            using var doc = JsonDocument.Parse(content);
            if (doc.RootElement.TryGetProperty("port", out var portElem)
                && portElem.TryGetInt32(out int port)
                && port is > 0 and <= 65535)
            {
                return port;
            }

            GD.PrintErr($"[SLAI] Invalid or missing 'port' in {configPath}, using default {DefaultPort}");
            return DefaultPort;
        }
        catch (Exception ex)
        {
            GD.PrintErr($"[SLAI] Failed to load config: {ex.Message}, using default port {DefaultPort}");
            return DefaultPort;
        }
    }

    public static void Initialize()
    {
        try
        {
            // Connect to main thread process frame for safe game-state reads
            var tree = (SceneTree)Engine.GetMainLoop();
            tree.Connect(SceneTree.SignalName.ProcessFrame, Callable.From(ProcessMainThreadQueue));

            int port = LoadPort();

            _listener = new HttpListener();
            _listener.Prefixes.Add($"http://localhost:{port}/");
            _listener.Prefixes.Add($"http://127.0.0.1:{port}/");
            _listener.Start();

            _serverThread = new Thread(ServerLoop)
            {
                IsBackground = true,
                Name = "SLAI_Server"
            };
            _serverThread.Start();

            GD.Print($"[SLAI] v{Version} read-only observer started on http://localhost:{port}/");
        }
        catch (Exception ex)
        {
            GD.PrintErr($"[SLAI] Failed to start: {ex}");
        }
    }

    private static void ProcessMainThreadQueue()
    {
        int processed = 0;
        while (_mainThreadQueue.TryDequeue(out var action) && processed < 10)
        {
            try { action(); }
            catch (Exception ex) { GD.PrintErr($"[SLAI] Main thread action error: {ex}"); }
            processed++;
        }
    }

    internal static Task<T> RunOnMainThread<T>(Func<T> func)
    {
        var tcs = new TaskCompletionSource<T>();
        _mainThreadQueue.Enqueue(() =>
        {
            try { tcs.SetResult(func()); }
            catch (Exception ex) { tcs.SetException(ex); }
        });
        return tcs.Task;
    }

    internal static Task RunOnMainThread(Action action)
    {
        var tcs = new TaskCompletionSource<bool>();
        _mainThreadQueue.Enqueue(() =>
        {
            try { action(); tcs.SetResult(true); }
            catch (Exception ex) { tcs.SetException(ex); }
        });
        return tcs.Task;
    }

    private static void ServerLoop()
    {
        while (_listener?.IsListening == true)
        {
            try
            {
                var context = _listener.GetContext();
                ThreadPool.QueueUserWorkItem(_ => HandleRequest(context));
            }
            catch (HttpListenerException) { break; }
            catch (ObjectDisposedException) { break; }
        }
    }

    private static void HandleRequest(HttpListenerContext context)
    {
        try
        {
            var request = context.Request;
            var response = context.Response;
            response.Headers.Add("Access-Control-Allow-Origin", "*");
            response.Headers.Add("Access-Control-Allow-Methods", "GET, OPTIONS");
            response.Headers.Add("Access-Control-Allow-Headers", "Content-Type");

            if (request.HttpMethod == "OPTIONS")
            {
                response.StatusCode = 204;
                response.Close();
                return;
            }

            // SLAI is read-only — refuse any mutating verbs cleanly.
            if (request.HttpMethod != "GET")
            {
                SendError(response, 405, "SLAI is read-only. Only GET requests are accepted.");
                return;
            }

            string path = request.Url?.AbsolutePath ?? "/";

            if (path == "/")
            {
                SendJson(response, new
                {
                    message = $"Hello from SLAI v{Version}",
                    status = "ok",
                    role = "read-only-observer",
                    upstream = "forked from STS2MCP by Yikun Ji (Kunologist)"
                });
            }
            else if (path == "/api/v1/singleplayer")
            {
                HandleGetState(request, response);
            }
            else if (path == "/api/v1/profiles")
            {
                HandleGetProfiles(response);
            }
            else if (path == "/api/v1/profile")
            {
                HandleGetProfile(response);
            }
            else if (path == "/api/v1/compendium")
            {
                HandleGetCompendium(response);
            }
            else if (path == "/api/v1/wiki")
            {
                HandleGetWiki(request, response);
            }
            else
            {
                SendError(response, 404, "Not found");
            }
        }
        catch (Exception ex)
        {
            try
            {
                SendError(context.Response, 500, $"Internal error: {ex.Message}");
            }
            catch { /* response may already be closed */ }
        }
    }

    private static void HandleGetState(HttpListenerRequest request, HttpListenerResponse response)
    {
        string format = request.QueryString["format"] ?? "json";

        try
        {
            var stateTask = RunOnMainThread(() => BuildGameState());
            var state = stateTask.GetAwaiter().GetResult();

            if (format == "markdown")
            {
                try
                {
                    SendText(response, FormatAsMarkdown(state), "text/markdown");
                }
                catch (Exception ex)
                {
                    GD.PrintErr($"[SLAI] FormatAsMarkdown failed, returning JSON: {ex}");
                    SendJson(response, state);
                }
            }
            else
            {
                SendJson(response, state);
            }
        }
        catch (Exception ex)
        {
            GD.PrintErr($"[SLAI] HandleGetState: {ex}");
            try
            {
                response.StatusCode = 500;
                SendJson(response, new Dictionary<string, object?>
                {
                    ["error"] = $"Failed to read game state: {ex.Message}",
                    ["exception_type"] = ex.GetType().FullName,
                    ["stack_trace"] = ex.StackTrace
                });
            }
            catch { /* response may be unusable */ }
        }
    }
}
