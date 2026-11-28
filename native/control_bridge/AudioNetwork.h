#pragma once
#include "Network.h"
#include <cstdint>
#include <cstring>
#include <limits>

#pragma pack(push, 1)
struct AudioPacket {
    uint32_t magic = 0x31414D54, kind = 1;
    uint64_t instance = 0, frame = 0;
    uint32_t rate = 48000;
    uint16_t channels = 2, frames = 512;
    std::array<float, 1024> pcm {};
};
#pragma pack(pop)
static_assert(sizeof(AudioPacket) == 4128);

template <size_t Count> class AudioQueue {
    std::array<AudioPacket, Count> packets;
    std::atomic<uint32_t> read {0}, write {0};
public:
    void reset() { read.store(0); write.store(0); }
    bool push(const AudioPacket& packet) {
        auto w = write.load(std::memory_order_relaxed);
        if (w-read.load(std::memory_order_acquire) >= Count) return false;
        packets[w%Count] = packet;
        write.store(w+1, std::memory_order_release); return true;
    }
    bool pop(AudioPacket& packet) {
        auto r = read.load(std::memory_order_relaxed);
        if (r == write.load(std::memory_order_acquire)) return false;
        packet = packets[r%Count]; read.store(r+1, std::memory_order_release); return true;
    }
};

// Sockets and blocking work belong only to this network thread, never process().
class AudioNetwork {
    AudioQueue<64> outgoing, incoming;
    std::thread worker;
    std::atomic<bool> running {false};
    uint64_t identity = 0, cursor = 0;
    AudioPacket building;
    std::array<std::array<float, 1024>, 64> dry {}, wet {};
    std::array<uint64_t, 64> tags {};
    uint32_t fill = 0;
public:
    static constexpr uint32_t delay = 4096;
    ~AudioNetwork() { stop(); }
    void start() {
        if (worker.joinable()) return;
        identity = static_cast<uint64_t>(std::chrono::steady_clock::now().time_since_epoch().count());
        cursor = 0; fill = 0; outgoing.reset(); incoming.reset();
        for (auto& block : dry) block.fill(0);
        tags.fill(std::numeric_limits<uint64_t>::max());
        running.store(true); worker = std::thread([this] { run(); });
    }
    void stop() { running.store(false); if (worker.joinable()) worker.join(); }
    void collect() {
        AudioPacket packet;
        for (int n = 0; n < 64 && incoming.pop(packet); ++n) {
            if (packet.instance != identity || packet.frame > cursor
                || (cursor > delay+512 && packet.frame+512 < cursor-delay)) continue;
            const auto index = (packet.frame/512)%64;
            wet[index] = packet.pcm; tags[index] = packet.frame/512;
        }
    }
    void sample(float left, float right, float& outLeft, float& outRight, double rate, bool enabled) {
        auto block = (cursor/512)%64;
        auto offset = static_cast<size_t>(cursor%512)*2;
        dry[block][offset] = left; dry[block][offset+1] = right;
        building.pcm[fill*2] = left; building.pcm[fill*2+1] = right;
        if (++fill == 512) {
            building.instance = identity; building.frame = cursor-511;
            building.rate = static_cast<uint32_t>(rate);
            if (rate == 48000) outgoing.push(building);
            fill = 0;
        }
        outLeft = outRight = 0;
        if (cursor >= delay) {
            auto target = cursor-delay;
            const auto index = (target/512)%64;
            const auto position = static_cast<size_t>(target%512)*2;
            const auto& source = enabled && tags[index] == target/512 ? wet[index] : dry[index];
            outLeft = source[position]; outRight = source[position+1];
        }
        ++cursor;
    }
private:
    void run() {
#ifdef _WIN32
        WSADATA data {};
        if (WSAStartup(MAKEWORD(2,2), &data) != 0) return;
        SOCKET channel = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (channel == INVALID_SOCKET) { WSACleanup(); return; }
        u_long nonblocking = 1; ioctlsocket(channel, FIONBIO, &nonblocking);
#else
        int channel = socket(AF_INET, SOCK_DGRAM, 0);
        if (channel < 0) return;
        timeval timeout {0, 1000}; setsockopt(channel, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
#endif
        sockaddr_in destination {};
        destination.sin_family = AF_INET; destination.sin_port = htons(26790);
        destination.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        while (running.load()) {
            AudioPacket packet;
            for (int n = 0; n < 64 && outgoing.pop(packet); ++n)
                sendto(channel, reinterpret_cast<const char*>(&packet), sizeof(packet), 0,
                       reinterpret_cast<sockaddr*>(&destination), sizeof(destination));
            for (int n = 0; n < 64; ++n) {
                sockaddr_in sender {};
#ifdef _WIN32
                int length = sizeof(sender);
#else
                socklen_t length = sizeof(sender);
#endif
                char raw[sizeof(AudioPacket)+1];
                int count = recvfrom(channel, raw, sizeof(raw), 0, reinterpret_cast<sockaddr*>(&sender), &length);
                if (count <= 0) break;
                if (count != sizeof(AudioPacket) || sender.sin_addr.s_addr != htonl(INADDR_LOOPBACK)
                    || sender.sin_port != htons(26790)) continue;
                std::memcpy(&packet, raw, sizeof(packet));
                if (packet.magic != 0x31414D54 || packet.kind != 2 || packet.instance != identity
                    || packet.rate != 48000 || packet.frames != 512 || packet.channels != 2 || packet.frame%512) continue;
                bool valid = true;
                for (float value : packet.pcm) if (!std::isfinite(value)) { valid = false; break; }
                if (valid) incoming.push(packet);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
#ifdef _WIN32
        closesocket(channel); WSACleanup();
#else
        close(channel);
#endif
    }
};
