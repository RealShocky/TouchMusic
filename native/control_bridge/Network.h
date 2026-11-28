#pragma once
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#endif
#include <array>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <thread>

// Only this worker owns the socket. The audio callback publishes scalar atomics.
class BridgeNetwork {
public:
    std::array<std::atomic<double>, 10> values;
    std::atomic<double> tempo {120}, ppq {0}, rate {48000}, position {0};
    std::atomic<double> stamp {0};
    std::atomic<bool> playing {false}, timingValid {false};
    BridgeNetwork() {
        for (auto& value : values) value.store(0);
        values[3].store(.5); values[5].store(1); values[6].store(.5);
        identity = static_cast<unsigned long long>(std::chrono::steady_clock::now().time_since_epoch().count());
    }
    ~BridgeNetwork() { stop(); }
    static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
    void start() {
        if (worker.joinable()) return;
        running.store(true);
        worker = std::thread([this] { run(); });
    }
    void stop() {
        running.store(false);
        if (worker.joinable()) worker.join();
    }
private:
    std::atomic<bool> running {false};
    std::thread worker;
    unsigned long long identity = 0;
    void run() {
#ifdef _WIN32
        WSADATA data {};
        if (WSAStartup(MAKEWORD(2,2), &data) != 0) return;
        SOCKET channel = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (channel == INVALID_SOCKET) { WSACleanup(); return; }
#else
        int channel = socket(AF_INET, SOCK_DGRAM, 0);
        if (channel < 0) return;
#endif
        sockaddr_in destination {};
        destination.sin_family = AF_INET;
        destination.sin_port = htons(26789);
        destination.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        unsigned long long sequence = 0;
        while (running.load()) {
            char buffer[1400];
            const bool valid = timingValid.load();
            const double elapsed = std::max(0., now()-stamp.load());
            const bool moving = playing.load() && elapsed < 1.;
            const int count = std::snprintf(buffer, sizeof(buffer),
                "{\"protocol\":\"touchmusic-control/1\",\"instance\":\"%llx\",\"sequence\":%llu,"
                "\"timing_valid\":%s,\"tempo\":%.8f,\"ppq\":%.8f,\"sample_rate\":%.1f,\"sample_position\":%.0f,"
                "\"playing\":%s,\"parameters\":[%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%.8f,%.8f]}",
                identity, ++sequence, valid ? "true" : "false", valid ? tempo.load() : 120.,
                valid ? ppq.load() + (moving ? elapsed*tempo.load()/60. : 0.) : 0.,
                rate.load(), position.load() + (moving ? elapsed*rate.load() : 0.), moving ? "true" : "false",
                values[0].load(), values[1].load(), values[2].load(), values[3].load(), values[4].load(),
                values[5].load(), values[6].load(), values[7].load(), values[8].load(), values[9].load());
            if (count > 0 && count < static_cast<int>(sizeof(buffer)))
                sendto(channel, buffer, count, 0, reinterpret_cast<sockaddr*>(&destination), sizeof(destination));
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
#ifdef _WIN32
        closesocket(channel); WSACleanup();
#else
        close(channel);
#endif
    }
};

