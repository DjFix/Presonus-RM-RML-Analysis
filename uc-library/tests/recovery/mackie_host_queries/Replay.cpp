#include "presonus/MackieControlModel.hpp"
#include <cstdlib>
#include <iostream>
#include <vector>
static std::vector<int> raw;
static unsigned calls;
static bool realRandom;
extern "C" int __real_rand();
extern "C" int __wrap_rand() {
  ++calls;
  return realRandom ? __real_rand() : raw.at((calls - 1) % 4);
}
struct Sink : Presonus::IMidiSink {
  std::vector<unsigned char> bytes;
  unsigned sends{}, port{};
  void sendMidiMessage(const unsigned char *data, unsigned size,
                       unsigned p) override {
    if (calls != 4 && calls != 8)
      std::abort();
    bytes.assign(data, data + size);
    port = p;
    ++sends;
  }
};
int main(int argc, char **argv) {
  if (argc != 16)
    return 2;
  const bool alternative = std::atoi(argv[1]);
  realRandom = std::atoi(argv[2]);
  const unsigned seed = std::strtoul(argv[3], nullptr, 10);
  Presonus::MackieControlModel model;
  Sink sink;
  model.applicationMidiSinkConfigured = true;
  model.applicationMidiSink = &sink;
  for (unsigned i = 0; i < 8; ++i)
    model.hostConnectionIdentity[i] = std::atoi(argv[4 + i]);
  for (unsigned i = 0; i < 4; ++i)
    raw.push_back(std::atoi(argv[12 + i]));
  for (unsigned repeat = 0; repeat < 2; ++repeat) {
    if (realRandom)
      std::srand(seed);
    if (alternative)
      model.sendHostConnectionQueryAlternative();
    else
      model.sendHostConnectionQuery();
  }
  if (calls != 8 || sink.sends != 2 || sink.port != 0)
    return 3;
  for (auto b : model.hostConnectionChallenge)
    std::cout << unsigned(b) << ' ';
  for (auto b : sink.bytes)
    std::cout << unsigned(b) << ' ';
  std::cout << '\n';
}
