#include "presonus/noaa/programmer.hpp"

namespace Presonus::NOAA {
TCardProgrammer::TCardProgrammer(UC::IFirmwareUpdateListener *listener,
                                 const unsigned char *image,
                                 unsigned int length)
    : transport_(&presonus::noaa::posixProgrammerTransport()) {
  state_.image = image;
  state_.length = length;
  state_.listener = listener;
}
TCardProgrammer::~TCardProgrammer() { close(); }

} // namespace Presonus::NOAA
