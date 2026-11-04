#include "presonus/dsp/Controller.hpp"
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
using namespace Presonus::Dsp;
class Probe final : public Controller {
public:
  // Original fixtures never exercise process updates; reject an unexpected
  // call.
  void doUpdates() override { std::abort(); }
  using Controller::Controller;
  float getValue(int) const override { return 0; }
  float setValue(int, float v) override { return v; }
};
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const auto bits =
      static_cast<std::uint32_t>(std::strtoull(argv[1], nullptr, 0));
  ParamDescriptorList list(presonus::dsp::DescriptorSourceTag{});
  const bool present = std::atoi(argv[2]) != 0;
  Probe p(std::bit_cast<int>(bits), present ? &list : nullptr);
  const auto &s = p.sourceState();
  std::cout << s.word04 << ' ' << s.word08 << ' ' << s.word10 << ' ' << s.word14
            << ' ' << std::bit_cast<std::uint32_t>(s.constructorId) << ' '
            << unsigned(s.processDirty) << ' ' << unsigned(s.byte1d) << ' '
            << s.word20 << ' ' << s.processRateBits << ' '
            << (s.descriptorList == (present ? &list : nullptr)) << ' '
            << (s.descriptors ==
                (present ? &list.sourceDescriptors() : nullptr))
            << ' ' << s.lookupByTag << '\n';
  // The adapter borrows the live vector, including growth after construction.
  if (present) {
    list.addFloat(73, "", "", "", 10, 30, 10, "", "", 20, 0);
    if (p.normalizedValueToRange(0, .5f) != 20)
      return 3;
    p.sourceState().lookupByTag = true;
    if (p.normalizedValueToRange(73, .5f) != 20)
      return 4;
  }
}
