using System;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AgriSenseGCS.Models;

namespace AgriSenseGCS.Services
{
    public class WebSocketService
    {
        private ClientWebSocket? _client;
        private CancellationTokenSource? _cts;

        public event Action<TelemetryPacket>? OnTelemetryReceived;
        public event Action<bool>? OnConnectionStateChanged;
        public bool IsConnected => _client?.State == WebSocketState.Open;

        public async Task ConnectAsync(string serverUrl)
        {
            if (IsConnected) return;

            _client = new ClientWebSocket();
            _cts = new CancellationTokenSource();

            try
            {
                await _client.ConnectAsync(new Uri(serverUrl), _cts.Token);
                OnConnectionStateChanged?.Invoke(true);
                _ = Task.Run(ReceiveLoopAsync, _cts.Token);
            }
            catch (Exception ex)
            {
                OnConnectionStateChanged?.Invoke(false);
                Console.WriteLine($"WebSocket Connection Error: {ex.Message}");
            }
        }

        private async Task ReceiveLoopAsync()
        {
            var buffer = new byte[16384];
            while (_client != null && _client.State == WebSocketState.Open && !_cts!.IsCancellationRequested)
            {
                try
                {
                    var result = await _client.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await _client.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                        OnConnectionStateChanged?.Invoke(false);
                        break;
                    }

                    string jsonStr = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    var packet = JsonSerializer.Deserialize<TelemetryPacket>(jsonStr);
                    if (packet != null)
                    {
                        OnTelemetryReceived?.Invoke(packet);
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Receive Error: {ex.Message}");
                    OnConnectionStateChanged?.Invoke(false);
                    break;
                }
            }
        }

        public async Task SendPresetTriggerAsync(string presetName)
        {
            if (!IsConnected || _client == null) return;

            var msg = JsonSerializer.Serialize(new { action = "simulate", preset = presetName });
            var bytes = Encoding.UTF8.GetBytes(msg);
            await _client.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
        }

        public async Task DisconnectAsync()
        {
            if (_client != null && _client.State == WebSocketState.Open)
            {
                _cts?.Cancel();
                await _client.CloseAsync(WebSocketCloseStatus.NormalClosure, "User Disconnected", CancellationToken.None);
                OnConnectionStateChanged?.Invoke(false);
            }
        }
    }
}
