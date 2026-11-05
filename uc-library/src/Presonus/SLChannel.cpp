#include "presonus/SLChannel.hpp"

namespace Presonus {
Core::Portable::Parameter *SLChannelBase::getSelectionParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getColorParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkMasterParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannelBase::getLinkedSelectionParameter() const {
  return nullptr;
}
Core::Portable::Parameter *SLChannel::getSelectionParameter() const {
  return selection_;
}
} // namespace Presonus
