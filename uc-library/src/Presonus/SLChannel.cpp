#include "presonus/SLChannel.hpp"

namespace Presonus {
Core::Portable::Parameter *SLChannelBase::getSelectionParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannel::getSelectionParameter() const {
  return selection_;
}
} // namespace Presonus
