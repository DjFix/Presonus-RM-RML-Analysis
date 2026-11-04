#include "presonus/dsp/SLReverbController.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

// Test-only boundary: the constructor never invokes unresolved setValue.
class Probe final : public Presonus::Dsp::SLReverbController {
public:
  // This fixture never exercises the unresolved process-update default.
  void doUpdates() override { std::abort(); }
  explicit Probe(int id) : SLReverbController(id) {}
  explicit Probe(presonus::dsp::ReverbPortState &state)
      : SLReverbController(state) {}
  float setValue(int, float) override {
    throw std::logic_error("unresolved setValue invoked by constructor");
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const int id = std::stoi(argv[1]);
  Probe c(id);
  const auto &base = c.sourceState();
  if (base.constructorId != id || base.descriptorList || base.descriptors ||
      base.lookupByTag || base.word04 || base.word08 != 0xffffffffU ||
      base.word10 || base.word14 || base.word20 || base.byte1d ||
      base.processDirty || base.processRateBits || !c.reverbBiquad())
    return 3;
  // Fixture observation projection uses named portable base slots; these
  // offsets describe native observations and do not assert host object layout.
  auto observation = c.reverbSourceState().memory;
  auto project = [&](std::size_t offset, std::uint32_t value) {
    std::memcpy(observation.data() + offset, &value, 4);
  };
  project(0x04, base.word04);
  project(0x08, base.word08);
  project(0x0c, 0); // independently checked descriptorList is null above
  project(0x10, base.word10);
  project(0x14, base.word14);
  project(0x18, static_cast<std::uint32_t>(base.constructorId));
  observation[0x1c] = std::byte{base.processDirty};
  observation[0x1d] = std::byte{base.byte1d};
  project(0x20, base.word20);
  project(0x24, base.processRateBits);
  for (auto b : observation)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << static_cast<unsigned>(b);
  std::cout << '\n';
  // Constructor array extent does not establish a value-count provider.
  if (c.reverbSourceState().valueCount)
    return 8;
  c.reverbSourceState().valueCount = [] { return 57; }; // test-only boundary
  c.setReverbValue(3, 0.5f);
  if (c.getValue(3) != 0.5f ||
      c.reverbSourceState().memory[0x1c] != std::byte{1})
    return 7;
  // Borrowed mode retains the same reference, callbacks and caller bytes;
  // setDirty/getValue work against that storage rather than an owned shadow.
  presonus::dsp::ReverbPortState state;
  state.valueCount = [] { return 57; };
  state.memory.fill(std::byte{0x5a});
  Probe borrowed(state);
  if (&borrowed.reverbSourceState() != &state || borrowed.reverbBiquad())
    return 4;
  borrowed.setReverbValue(7, 0.25f);
  if (borrowed.getValue(7) != 0.25f || state.memory[0x1c] != std::byte{1})
    return 5;
  borrowed.setDirty();
  if (state.memory[0x144 + 3] != std::byte{0xbf})
    return 6;
}
