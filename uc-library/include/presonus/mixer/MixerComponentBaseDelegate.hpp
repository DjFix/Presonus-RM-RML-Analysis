#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
namespace Presonus::Mixer {
// Partial original nested interface. Native primary-table identities establish
// these encoded methods. Void returns and host layout remain source-port
// declarations; unsupported pure markers do not claim original purity.
class MixerComponentBase::Delegate {
public:
  virtual void selectionChanged() {}
  virtual void linkChanged() {}
  virtual void clientsChanged() = 0;
  virtual void notifyStoring(bool);
  virtual void faderLocateDirty(ChannelComponent *);

protected:
  ~Delegate() = default;
};
} // namespace Presonus::Mixer
