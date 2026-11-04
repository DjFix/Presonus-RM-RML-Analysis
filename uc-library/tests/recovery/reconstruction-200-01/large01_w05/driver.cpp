#include "presonus/DAWTimeInfo.hpp"
#include "presonus/IDAWTimeInfo.hpp"
#include "presonus/surface/TransportHandler.hpp"
#include "presonus/uc/misc_events.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <new>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void word(std::uint8_t *p, std::uint32_t v, unsigned n = 4) {
  for (unsigned i = 0; i < n; ++i)
    p[i] = v >> (8 * i);
}
void real(std::uint8_t *p, double v) {
  std::uint64_t b;
  std::memcpy(&b, &v, 8);
  for (unsigned i = 0; i < 8; ++i)
    p[i] = b >> (8 * i);
}
void hex(const std::uint8_t *p, unsigned n) {
  for (unsigned i = 0; i < n; ++i)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << unsigned(p[i]);
  std::cout << std::dec << '\n';
}
} // namespace
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string kind;
    in >> kind;
    if (kind == "getter") {
      int target, seed;
      in >> target >> seed;
      alignas(Presonus::DAWTimeInfo::TimeString) std::array<std::uint8_t, 512>
          bytes;
      bytes.fill(seed);
      Presonus::DAWTimeInfo obj(bytes.data());
      auto p = target == 1 ? obj.getLoopStartTime() : obj.getTransportTime();
      auto result = reinterpret_cast<const std::uint8_t *>(p) - bytes.data();
      Presonus::DAWTimeInfo::State s;
      Presonus::DAWTimeInfo stateful(bytes.data(), s);
      if (stateful.getTransportTime() != &s.times[0] ||
          stateful.getLoopStartTime() != &s.times[1])
        return 3;
      std::cout << result << '\n';
    } else if (kind == "name") {
      Presonus::Surface::TransportHandler obj;
      std::cout << obj.getName() << '\n';
    } else if (kind == "destructor") {
      unsigned seed;
      in >> seed;
      presonus::dawtime::DispatchState state;
      state.identity = std::uint32_t(seed) * 0x01010101u;
      state.unchanged.fill(seed);
      const auto initialIdentity = state.identity;
      {
        Presonus::IDAWTimeInfo object(state);
        // Construction borrows state and must not manufacture a reset.
        if (state.identity != initialIdentity)
          return 4;
      }
      // Observe actual production destructor writes in the still-live borrowed
      // state. No bytes of the destroyed C++ object are inspected.
      if (state.identity != 1691928)
        return 4;
      if (!std::all_of(state.unchanged.begin(), state.unchanged.end(),
                       [seed](auto b) { return b == seed; }))
        return 5;
      std::cout << "base-vptr-only" << '\n';
    } else if (kind == "bar") {
      int n, value;
      in >> n;
      std::vector<std::uint8_t> records(24 * std::max(n, 1));
      for (int i = 0; i < n; ++i) {
        int bar;
        in >> bar;
        real(records.data() + 24 * i, double(i));
        word(records.data() + 24 * i + 8, 4);
        word(records.data() + 24 * i + 12, 4);
        word(records.data() + 24 * i + 16, bar);
      }
      in >> value;
      Presonus::DAWTimeInfo::TimeSignatureMap map(records.data(), n);
      auto p = map.findItemByBar(value);
      std::cout << (n ? (p - records.data()) / 24 : -1) << ' ';
      hex(p, 24);
    } else if (kind == "tempo") {
      int n;
      in >> n;
      std::vector<std::uint8_t> records(24 * std::max(n, 1));
      for (int i = 0; i < n; ++i)
        for (int j = 0; j < 3; ++j) {
          double value;
          in >> value;
          real(records.data() + 24 * i + 8 * j, value);
        }
      double value;
      in >> value;
      Presonus::DAWTimeInfo::TempoMap map(records.data(), n);
      auto result = map.secondsToPpq(value);
      std::uint8_t bytes[8];
      real(bytes, result);
      hex(bytes, 8);
    } else if (kind == "delta") {
      unsigned musical, blocked, count;
      int delta;
      in >> musical >> blocked >> count >> delta;
      Presonus::DAWTimeInfo::TimeString time;
      std::array<std::int32_t, 4> values;
      for (auto &v : values)
        in >> v;
      time.clockValues = time.musicalValues = values;
      std::array<std::uint8_t, 72> records{};
      int bars[] = {0, 2, 4}, nums[] = {4, 3, 7};
      for (int i = 0; i < 3; ++i) {
        real(records.data() + 24 * i, double(i));
        word(records.data() + 24 * i + 8, nums[i]);
        word(records.data() + 24 * i + 12, 4);
        word(records.data() + 24 * i + 16, bars[i]);
      }
      Presonus::DAWTimeInfo::TimeSignatureMap map(records.data(), 3);
      Presonus::DAWTimeInfo::State state;
      state.locating = blocked;
      state.musicalDisplay = musical;
      state.signatureMap = &map;
      std::array<std::uint8_t, 512> borrowed{};
      Presonus::DAWTimeInfo obj(borrowed.data(), state);
      Presonus::UC::TimeCodeEvent event;
      event.header.type = event.header.reserved04 = event.header.routeA =
          event.header.routeB = 0xa5a5a5a5;
      event.keyBits = 0xa5a5a5a5;
      event.recordCount = count;
      event.reserved15.fill(0xa5);
      for (auto &r : event.records) {
        r.a = r.b = 0xa5;
        r.reserved.fill(0xa5);
        r.rawBytes.fill(0xa5);
      }
      obj.createDeltaTimeEvent(event, delta, time);
      // Explicit projection into native semantic offsets; no host layout claim.
      std::array<std::uint8_t, 112> projected;
      projected.fill(0xa5);
      word(projected.data(), event.header.type);
      word(projected.data() + 4, event.header.reserved04);
      word(projected.data() + 8, event.header.routeA);
      word(projected.data() + 12, event.header.routeB);
      word(projected.data() + 16, event.keyBits);
      projected[20] = event.recordCount;
      std::copy(event.reserved15.begin(), event.reserved15.end(),
                projected.begin() + 21);
      for (unsigned i = 0; i < 4; ++i) {
        const auto &r = event.records[i];
        projected[24 + 16 * i] = r.a;
        projected[25 + 16 * i] = r.b;
        std::copy(r.reserved.begin(), r.reserved.end(),
                  projected.begin() + 26 + 16 * i);
        std::copy(r.rawBytes.begin(), r.rawBytes.end(),
                  projected.begin() + 32 + 16 * i);
      }
      hex(projected.data(), projected.size());
    } else
      return 2;
  }
}
