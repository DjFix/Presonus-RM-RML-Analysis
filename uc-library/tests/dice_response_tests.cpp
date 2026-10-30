#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
#include <zlib.h>

// Independent concrete fixture: the original base accepts slot stays pure.
class NoaaFixtureReceiver final : public Presonus::NOAA::SysexReceiver {
public:
  bool accepts(const Presonus::NOAA::SysexPacket &) override { return false; }
};

static void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
static std::int64_t signedBits(std::uint64_t bits) {
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
struct Event {
  char kind;
  std::uint64_t ticks;
  std::uint32_t first, second, ackBefore, wordBefore, ackAfter, wordAfter;
};
template <class Receiver>
class Script final : public presonus::dice::ResponseServices {
public:
  Receiver &receiver;
  unsigned int &response;
  std::vector<Event> events;
  int mutateAt = -1;
  std::uint32_t newAck = 256;
  std::uint64_t newWord = 0x100000000ULL;
  std::size_t position = 0;
  Script(Receiver &receiver, unsigned int &response)
      : receiver(receiver), response(response) {}
  const Event &step(char kind, std::uint32_t first = 0,
                    std::uint32_t second = 0) {
    require(position < events.size(), "unexpected boundary");
    const auto &event = events[position];
    require(event.kind == kind && event.first == first &&
                event.second == second,
            "boundary order/arguments");
    require(receiver.portableState().command == event.ackBefore &&
                response == event.wordBefore,
            "boundary state before");
    if (static_cast<int>(position) == mutateAt) {
      if (newAck < 256)
        receiver.portableState().command = static_cast<unsigned char>(newAck);
      if (newWord < 0x100000000ULL)
        response = static_cast<unsigned int>(newWord);
    }
    if (position == 31) {
      receiver.portableState().command = 17;
      response = 0x80000000U;
    }
    require(receiver.portableState().command == event.ackAfter &&
                response == event.wordAfter,
            "boundary state after");
    ++position;
    return event;
  }
  std::int64_t clockRawTicks() override { return signedBits(step('C').ticks); }
  void pumpIdle(bool force) override { step('P', force ? 1U : 0U); }
  void sleepMilliseconds(std::uint32_t milliseconds) override {
    step('S', milliseconds);
  }
  void timeoutNotice(bool responseSet, std::uint32_t value,
                     std::uint32_t timeoutLow) override {
    step(responseSet ? 'R' : 'A', value, timeoutLow);
  }
};

template <class Receiver> static unsigned replay(const char *fixture) {
  gzFile input = gzopen(fixture, "rb");
  require(input != nullptr, "fixture open");
  std::array<char, 65536> buffer{};
  unsigned cases = 0;
  while (gzgets(input, buffer.data(), buffer.size())) {
    std::istringstream row(buffer.data());
    unsigned mode, initialAck, initialWord, result, finalAck, finalWord, count;
    std::uint64_t timeoutBits;
    Receiver receiver;
    unsigned int response = 0;
    Script<Receiver> script(receiver, response);
    row >> mode >> timeoutBits >> initialAck >> initialWord >>
        script.mutateAt >> script.newAck >> script.newWord >> result >>
        finalAck >> finalWord >> count;
    require(!row.fail() && mode <= 1 && count <= 40, "fixture header");
    response = initialWord;
    auto &state = receiver.portableState();
    state.command = static_cast<unsigned char>(initialAck);
    state.status = static_cast<unsigned char>(initialAck ^ 0x5a);
    state.infoWords = {0x11223344, 0x55667788, 0x99aabbcc};
    state.rateWord = 0xa5a5a5a5;
    state.clockWord = 0x5a5a5a5a;
    const auto before = state;
    for (unsigned index = 0; index < count; ++index) {
      Event event;
      row >> event.kind >> event.ticks >> event.first >> event.second >>
          event.ackBefore >> event.wordBefore >> event.ackAfter >>
          event.wordAfter;
      require(!row.fail(), "fixture event");
      script.events.push_back(event);
    }
    receiver.setPortableResponseServices(script);
    const long long timeout = static_cast<long long>(signedBits(timeoutBits));
    const unsigned actual = mode == 0
                                ? receiver.waitAck(timeout)
                                : receiver.waitResponseSet(response, timeout);
    require(actual == result && state.command == finalAck &&
                response == finalWord,
            "return/state mismatch");
    require(script.position == script.events.size(), "missing boundary");
    require(state.status == before.status &&
                state.infoWords == before.infoWords &&
                state.rateWord == before.rateWord &&
                state.clockWord == before.clockWord,
            "unrelated state changed");
    ++cases;
  }
  require(gzclose(input) == Z_OK, "fixture close");
  return cases;
}
int main(int argc, char **argv) {
  try {
    require(argc == 3, "fixture and original namespace role required");
    const unsigned cases =
        std::string(argv[2]) == "client"
            ? replay<presonus::dice::fixture::ConcreteReceiver>(argv[1])
            : replay<NoaaFixtureReceiver>(argv[1]);
    std::cout << "PASS " << cases
              << " original ARM wait return/state/ordered-boundary fixtures\n";
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
