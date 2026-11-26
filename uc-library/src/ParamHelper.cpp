#include "presonus/uc/ParamHelper.hpp"

#include "core/portable/coreparams.h"
#include "core/public/coreformatter.h"
#include "core/public/coreinterpolator.h"
#include "presonus/uc/parameter_events.hpp"

#include <algorithm>
#include <cstring>

namespace {
float rangeValue(std::uint32_t bits) {
  float value;
  static_assert(sizeof(value) == sizeof(bits));
  std::memcpy(&value, &bits, sizeof(value));
  return value;
}
} // namespace

namespace ParamHelper {
void applyRange(Core::Portable::Parameter *parameter,
                const Presonus::UC::ParamRangeEvent &event) {
  std::array<char, 33> formatterName{};
  std::copy(event.labels[1].begin(), event.labels[1].end(),
            formatterName.begin());
  parameter->setFormatter(Core::FormatterRegistry::find(formatterName.data()));

  const auto minimum = rangeValue(event.wordBits[1]);
  const auto maximum = rangeValue(event.wordBits[2]);
  if (auto *numeric = Core::Portable::NumericParam::cast(parameter)) {
    std::array<char, 33> interpolatorName{};
    std::copy(event.labels[0].begin(), event.labels[0].end(),
              interpolatorName.begin());
    auto *interpolator =
        Core::InterpolatorFactory::create(interpolatorName.data());
    if (interpolator)
      interpolator->setRange(minimum, maximum, rangeValue(event.wordBits[3]));
    numeric->setInterpolator(interpolator);
  }

  parameter->setMin(minimum);
  parameter->setMax(maximum);
  parameter->setDefault(rangeValue(event.wordBits[4]));
}
} // namespace ParamHelper
