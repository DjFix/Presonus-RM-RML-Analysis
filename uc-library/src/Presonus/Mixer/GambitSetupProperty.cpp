#include "presonus/mixer/setup_property_applications.hpp"
namespace Presonus::Mixer {
NOAA::NOAASetupProperty GambitApplication::getNOAASetupProperty() const {
  const auto &context = portableSetupContext();
  return NOAA::NOAASetupProperty("/dev/spidev0.3", context.alreadyAdjusted0c,
                                 presonus::noaa::rm13731GambitRouterSlots(), 24,
                                 context.native20);
}
} // namespace Presonus::Mixer
