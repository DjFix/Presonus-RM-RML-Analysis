#include "presonus/DefaultMeterInterpolator.hpp"

#include <bit>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <memory>
#include <string_view>

namespace {

class CurveProbe : public DefaultMeterInterpolator {
public:
  const BreakPoint &point(int index) const { return breakPoints[index]; }
  int pointCount() const { return numPoints; }
};

const void *addressPoint(const Core::Interpolator &instance) {
  const void *address{};
  std::memcpy(&address, &instance, sizeof(address));
  return address;
}

void printBits(float value) {
  std::cout << ' ' << std::bit_cast<std::uint32_t>(value);
}

} // namespace

int main() {
  using Curve = Core::SegmentInterpolator;
  using Factory = Core::InterpolatorFactory;
  using Pointer = std::unique_ptr<Core::Interpolator>;

  constexpr Curve::BreakPoint standalonePoints[]{{0.f, 7.f}, {1.f, 11.f}};
  const DefaultMeterInterpolator standalone(2, standalonePoints);
  if (standalone.normalizedToRange(0.25f) != 8.f ||
      standalone.rangeToNormalized(10.f) != 0.75f)
    return 1;

  __initMeterControl();
  const Pointer original(Factory::create("audiometer"));
  const Pointer again(Factory::create("audiometer"));
  const CurveProbe defaultCurve;
  if (!original || !again ||
      addressPoint(*original) != addressPoint(standalone) ||
      addressPoint(*again) != addressPoint(standalone) ||
      original.get() == again.get() || !original->getName() ||
      std::string_view(original->getName()) != "audiometer" ||
      defaultCurve.pointCount() != 13)
    return 2;

  for (int i = 0; i < defaultCurve.pointCount(); ++i) {
    std::uint32_t decibelBits = 0;
    if (!(std::cin >> decibelBits))
      return 3;
    const float decibels = std::bit_cast<float>(decibelBits);
    const float exponent = decibels * 0.05f;
    const float hostPower = ::powf(10.f, exponent);
    const auto &[amplitude, level] = defaultCurve.point(i);
    printBits(exponent);
    printBits(hostPower);
    printBits(amplitude);
    printBits(level);
    printBits(original->normalizedToRange(amplitude));
    printBits(again->rangeToNormalized(level));
    std::cout << '\n';
  }
}
