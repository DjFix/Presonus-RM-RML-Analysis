#pragma once
#include "core/portable/coreparams.h"
#include "core/portable/corestorage.h"
#include "core/public/corevector.h"

namespace Presonus::Mixer {
class MixerComponentBase;
}
namespace presonus::mute_group_port {
struct UnboundCompatibility {};
// Borrowed, distinct native collections; independent binding, no mixer layout
// claim.
struct ChannelMute {
  const char *parentName;
  const char *name;
  Core::Portable::Parameter *mute;
};
struct MixerData {
  Core::Vector<Core::Portable::Parameter *> allMutes;
  Core::Vector<ChannelMute> channels;
};
// Independent source-port state. No original class layout or ownership claim.
struct State {
  Core::Portable::Parameter *active = nullptr;
  Core::Portable::Parameter *status = nullptr;
  Core::Portable::Parameter *alternateStatus = nullptr;
  Core::Vector<Core::Portable::Parameter *> members;
};
} // namespace presonus::mute_group_port

namespace Presonus {
// Original method scopes and encoded arguments; unencoded returns and layout
// remain unresolved. Provider API selection is an intentional source
// adaptation.
class MuteGroupBase {
public:
  // Source-port provider contract; original inheritance/layout/return
  // declaration are not established by the ELF. CCL owns the real parameter
  // representation.
  class Filter : public Core::Portable::IStorageFilter {
  public:
    void *castTo(TypeID typeId) override {
      return typeId == Core::Portable::IStorageFilter::kTypeID ? this : nullptr;
    }
    bool shouldLoad(int typeId, const char *name, void *object) const override;
    bool shouldSave(int typeId, const char *name, void *object) const override;
  };
  explicit MuteGroupBase(presonus::mute_group_port::State &state)
      : state(state) {}
  explicit MuteGroupBase(Mixer::MixerComponentBase &mixer);
  // Independent compatibility construction; not a recovered original ctor.
  explicit MuteGroupBase(presonus::mute_group_port::UnboundCompatibility)
      : state(ownedState) {}
  virtual ~MuteGroupBase();
  void portableBindMixerData(presonus::mute_group_port::MixerData &data) {
    mixerData = &data;
  }
  const Mixer::MixerComponentBase *portableMixer() const { return mixer; }
  int portableMemberCount() const { return state.members.count(); }
  void updateActive();
  void updateStatus();
  bool groupDirty() const;
  bool validStatus(Core::Portable::Parameter *parameter) const;
  void deactivate();

protected:
  presonus::mute_group_port::State ownedState;
  presonus::mute_group_port::State &state;
  Mixer::MixerComponentBase *mixer = nullptr;
  presonus::mute_group_port::MixerData *mixerData = nullptr;
};
} // namespace Presonus
