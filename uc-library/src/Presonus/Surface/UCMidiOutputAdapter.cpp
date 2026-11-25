#include "presonus/surface/UCMidiOutputAdapter.hpp"

#include <stdexcept>

namespace Presonus::Surface {
UCMidiOutputAdapter::UCMidiOutputAdapter() = default;

UCMidiOutputAdapter::~UCMidiOutputAdapter() {
  if (fader_)
    fader_->setMidiSink(nullptr);
}

void UCMidiOutputAdapter::setFaderUnit(IFaderUnit *unit, int) {
  auto *next = dynamic_cast<MackieFaderUnitBinding *>(unit);
  if (unit && !next)
    throw std::invalid_argument(
        "A portable Mackie fader unit binding is required");
  if (fader_)
    fader_->setMidiSink(nullptr);
  fader_ = next;
  if (fader_)
    fader_->setMidiSink(this);
}

void UCMidiOutputAdapter::sendMidiMessage(const unsigned char *data,
                                          unsigned length, unsigned port) {
  if (endpoint_)
    endpoint_->sendMidiMessage(data, length, port);
}
} // namespace Presonus::Surface
