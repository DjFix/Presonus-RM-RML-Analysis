#include "presonus/surface/TransportHandler.hpp"
namespace Presonus::Surface {
TransportHandler::~TransportHandler() = default;
const char *TransportHandler::getName() const { return "transport"; }
void TransportHandler::setAndObserve(Core::Portable::Parameter *&slot,
                                     Core::Portable::Parameter *parameter) {
  if (slot)
    slot->removeObserver(this);
  slot = parameter;
  if (parameter)
    parameter->addObserver(this);
}
} // namespace Presonus::Surface
