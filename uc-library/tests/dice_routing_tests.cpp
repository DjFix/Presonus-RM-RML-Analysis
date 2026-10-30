#include "presonus/dice/manager.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

int signedWord(std::uint32_t word) {
  int value;
  std::memcpy(&value, &word, 4);
  return value;
}
struct Event {
  std::uint32_t endpoint;
  presonus::dice::RouteTuple route;
};
struct RecordingSink : presonus::dice::RouteSink {
  std::vector<Event> *events = nullptr;
  std::array<std::uint32_t, 4> *returns = nullptr;
  Presonus::DICE::Dice3Manager *manager = nullptr;
  RecordingSink *other = nullptr;
  unsigned id = 0;
  bool swap = false;
  std::int32_t setRoute(const presonus::dice::RouteTuple &route) override {
    const auto result = (*returns)[events->size() % 4];
    events->push_back({id, route});
    if (swap)
      manager->setPortableRouteSink(*other);
    return signedWord(result);
  }
};
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::runtime_error("fixture path required");
    std::ifstream input(argv[1]);
    if (!input)
      throw std::runtime_error("fixture open failed");
    char op;
    std::uint32_t a, b, c, swap, expected, eventCount;
    std::array<std::uint32_t, 4> returns{};
    std::map<char, unsigned> counts;
    while (input >> op >> std::hex >> a >> b >> c >> returns[0] >> returns[1] >>
           returns[2] >> returns[3] >> swap >> expected >> eventCount) {
      std::vector<Event> events;
      RecordingSink first, second;
      first.events = second.events = &events;
      first.returns = second.returns = &returns;
      first.id = 1;
      second.id = 2;
      first.other = &second;
      second.other = &first;
      first.swap = second.swap = swap != 0;
      Presonus::DICE::Dice3Manager manager(first);
      first.manager = second.manager = &manager;
      std::int32_t result;
      if (op == 'P')
        result = manager.setDiceRoutingProfile(
            static_cast<Presonus::DICE::Dice3RoutingProfile>(signedWord(a)));
      else if (op == 'M')
        result = manager.setDiceMonitorSource(signedWord(a), signedWord(b),
                                              signedWord(c));
      else
        throw std::runtime_error("unknown operation");
      if (static_cast<std::uint32_t>(result) != expected ||
          events.size() != eventCount)
        throw std::runtime_error("return/callback count mismatch");
      for (unsigned i = 0; i < eventCount; ++i) {
        Event wanted{};
        if (!(input >> wanted.endpoint >> wanted.route.sinkDevice >>
              wanted.route.sink >> wanted.route.sourceDevice >>
              wanted.route.source))
          throw std::runtime_error("incomplete route event");
        const auto &e = events[i];
        if (e.endpoint != wanted.endpoint ||
            e.route.sinkDevice != wanted.route.sinkDevice ||
            e.route.sink != wanted.route.sink ||
            e.route.sourceDevice != wanted.route.sourceDevice ||
            e.route.source != wanted.route.source)
          throw std::runtime_error(
              "ordered endpoint/route tuple mismatch at callback" +
              std::to_string(i));
      }
      ++counts[op];
    }
    if (!input.eof() || counts.size() != 2)
      throw std::runtime_error("incomplete fixtures");
    std::cout << "PASS:";
    for (const auto &[op, count] : counts)
      std::cout << ' ' << op << '=' << std::dec << count;
    std::cout
        << " exact original ARM return and ordered route/endpoint callbacks\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
