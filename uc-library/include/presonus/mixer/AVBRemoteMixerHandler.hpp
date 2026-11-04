#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include <vector>
namespace Presonus {
class MixerClientComponentBase;
}
namespace presonus::mixer {
// Independent required application boundary for observed vector slot-zero
// dispatch. It has no default implementation. Original element declarations,
// ownership and ARM layouts remain unresolved.
struct RemoteMixerConnector {
  virtual void setComponent(Presonus::MixerClientComponentBase *) = 0;

protected:
  ~RemoteMixerConnector() = default;
};
struct RemoteMixerState {
  Presonus::MixerClientComponentBase *component = nullptr;
  Core::Portable::Parameter *activation = nullptr;
  Core::Portable::Parameter *savedSelection = nullptr;
  std::vector<RemoteMixerConnector *> connectors;
  std::vector<RemoteMixerConnector *> activators;
};
} // namespace presonus::mixer
namespace Presonus::Mixer {
// Source port using actual pinned CCL. This base is a source integration
// choice; exact original inheritance/layout and ordinary return spellings
// unproved.
class AVBRemoteMixerHandler : public Core::Portable::Component {
public:
  explicit AVBRemoteMixerHandler(presonus::mixer::RemoteMixerState &);
  ~AVBRemoteMixerHandler() override;
  void activate();
  void onRestoredSelection();
  void paramChanged(Core::Portable::Parameter *, int) override;
  void setMixerComponent(Presonus::MixerClientComponentBase *);
  void connect();

private:
  presonus::mixer::RemoteMixerState &state_;
};
} // namespace Presonus::Mixer
