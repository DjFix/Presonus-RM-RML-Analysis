#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corefilename.h"
#include "core/portable/corestorage.h"
#include "presonus/MuteGroupBase.hpp"
#include "presonus/delay_timer.hpp"
#include "presonus/uc/message_attributes.hpp"

namespace Presonus::Mixer {
class MixerComponentBase;
}
namespace Presonus::Panel {
class PresetNameManager;
}
namespace Presonus {
class StormMuteGroupComponent;
}
namespace presonus::storm_mute_port {
// Independent application bindings, not recovered original layouts, RTTI or
// delegate interfaces. All objects/arrays are borrowed and must remain stable.
struct Group {
  explicit Group(mute_group_port::State &state)
      : state(state), implementation(state) {}
  mute_group_port::State &state;
  Presonus::MuteGroupBase implementation;
  bool file = false;
  bool all = false;
  bool busy = false;
  bool stored = false;
};
struct Observer {
  virtual ~Observer() = default;
  virtual void allDirty(Presonus::StormMuteGroupComponent &, bool) = 0;
  virtual void groupDirty(Presonus::StormMuteGroupComponent &, unsigned int,
                          bool) = 0;
};
// Required unresolved application services. No fake MixerComponentBase,
// FileMuteGroup or AVBCascadeManager declarations are supplied.
struct Services {
  virtual ~Services() = default;
  virtual void refreshSip() = 0;
  virtual void activate(unsigned int) = 0;
  virtual Core::Portable::Component *connectedClient() = 0;
  virtual void muteGroupStored(int) = 0;
  virtual bool load(Group &) = 0;
};
// Explicit fixture boundary only. Production timers use real DelayTimer.
struct TimerFixture {
  virtual ~TimerFixture() = default;
  virtual bool executing() const = 0;
  virtual bool elapsed() const = 0;
  virtual void end() = 0;
  virtual void reset() = 0;
};
// Unbound operations throw; only optional store slots may be skipped with
// present().
struct Timer {
  Presonus::DelayTimer *production = nullptr;
  TimerFixture *fixture = nullptr;
  bool present() const { return production || fixture; }
  bool executing() const;
  bool elapsed() const;
  void end() const;
  void reset() const;
};
struct State {
  explicit State(Services &services) : services(services) {}
  Services &services;
  // Borrowed ordered parameter list observed by cleanup; independent storage.
  Core::Vector<Core::Portable::Parameter *> cleanupParameters;
  Core::Vector<Group *> groups;
  Group *allGroup = nullptr;
  Observer *observer = nullptr;
  void *delegate =
      nullptr; // Opaque borrowed original Delegate, no interface/layout claim.
  Core::Vector<Core::Portable::Parameter *> loose;
  Core::Vector<Core::Portable::Parameter *> delayed;
  Core::Vector<Core::Portable::Parameter *> mixerMutes;
  Core::Vector<Timer> storeTimers;
  Timer releaseTimer;
  // Borrowed actual application tree and cache manager; source-port bindings,
  // not recovered original fields or ARM layout. Null manager uses CCL
  // singleton.
  Presonus::Mixer::MixerComponentBase *mixer = nullptr;
  Presonus::Panel::PresetNameManager *presetNames = nullptr;
  bool enabled = true;
  bool recalling = false;
};
} // namespace presonus::storm_mute_port
namespace Presonus {
// Intentional portable source port bound to real pinned Core. Inheritance,
// returns and independent state storage do not establish original ARM ABI.
class StormMuteGroupComponent : public Core::Portable::Component {
public:
  // Source-port construction borrows the existing loose/safe-list state.
  // Original filter layout and constructor identity are not claimed.
  class SafeMuteFilter : public Core::Portable::IStorageFilter {
  public:
    explicit SafeMuteFilter(presonus::storm_mute_port::State &state)
        : safeList(state.loose) {}
    void *castTo(TypeID id) override {
      return id == Core::Portable::IStorageFilter::kTypeID
                 ? static_cast<Core::Portable::IStorageFilter *>(this)
                 : nullptr;
    }
    bool shouldLoad(int typeId, const char *name, void *object) const override;
    bool shouldSave(int typeId, const char *name, void *object) const override;

  private:
    Core::Vector<Core::Portable::Parameter *> &safeList;
  };
  // Provisional source-port aggregate return and static pointer declaration.
  // Native string output is observed; original return/constness/ARM layout are
  // not established. The original constructor/lifecycle is outside this port.
  Core::CStringBuffer<32> createDefaultName(int index) const;
  static const char *kDefaultName;
  explicit StormMuteGroupComponent(presonus::storm_mute_port::State &state)
      : state(state) {}
  ~StormMuteGroupComponent();
  class Delegate;
  void setDelegate(Delegate *);
  unsigned int getSwitchTag(unsigned int);
  bool isParamInAnyMuteGroup(Core::Portable::Parameter *);
  void cleanup();
  // Source-port FileName/void return declarations follow observed uses;
  // original ordinary return spellings and ARM aggregate ABI stay unresolved.
  Core::Portable::FileName getFileName(unsigned int) const;
  Core::Portable::FileName getSafeListFileName() const;
  void storeSafeList();
  void onAllMutesChange(bool);
  void startup();
  bool recallMutes(unsigned int, bool);
  void onObserveredParamChanged(Core::Portable::Parameter *, int);
  void onCascadeStateChange(bool);
  void onMuteChanged(Core::Portable::Parameter *);
  void groupWasStored(unsigned int);
  void refreshGroups();
  void notify(const UC::MessageAttributes &);
  void onIdle() override;
  void setAll(bool) const;
  void deactivate(unsigned int) const;
  // Actual provider observer entry point; original paramChanged target outside
  // this batch is not claimed reconstructed by this source-port forwarding.
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    onObserveredParamChanged(p, msg);
  }

private:
  presonus::storm_mute_port::Group *group(unsigned int) const;
  presonus::storm_mute_port::State &state;
};
} // namespace Presonus
