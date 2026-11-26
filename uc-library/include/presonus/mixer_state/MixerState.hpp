#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include <array>
#include <cstdint>

namespace Presonus {
// Original type identity is encoded by mangling. Enumerator names and the
// original underlying declaration remain unresolved; portable domain is int32.
enum ChannelType : int {};

// Independent semantic storage, not an original ARM object representation.
// Nonzero link words are tested without dereferencing or inventing pointee
// types.
class MixerClientComponentBase;

// Observed local preset values. The original enum declaration and underlying
// type remain unresolved.
class IPresetHandler {
public:
  // Opaque source-port identity used by the borrowed local roster.
  struct Preset {};
  enum PresetType : int {
    Scene,
    Channel,
    Geq,
    Reverb,
    Delay,
    MixScene,
    MuteGroup
  };

  // Portable borrowed string with static storage duration.
  const char *getEmptyPresetString() const;

  // Portable default hook. The firmware's exact declaration and virtual
  // layout remain unresolved.
  void loadPreset(PresetType, int, Core::CStringBuffer<128> &, const char *,
                  int);
  void endAuditioningPresets(PresetType, bool);
  void savePreset(PresetType, int, Core::CStringBuffer<128> &, const char *,
                  int);
  void auditionPreset(PresetType, int, Core::CStringBuffer<128> &, const char *,
                      int);
  void beginAuditioningPresets(PresetType, int);
  void renamePreset(PresetType, int, Core::CStringBuffer<128> &, const char *);
  void deletePreset(PresetType, int, Core::CStringBuffer<128> &, const char *);
};

struct PortableMixerState {
  std::uint32_t masterWord = 0;
  std::uint32_t slaveWord = 0;
  bool hasGeqConfiguration = false;
  std::uint32_t geqCountWord = 0;
  // Borrowed identities and GEQ list. No ownership or remote behavior.
  MixerClientComponentBase *masterMixer = nullptr;
  MixerClientComponentBase *slaveMixer = nullptr;
  const Core::ConstVector<Core::Portable::Component *> *geqs = nullptr;
  using PresetRoster = Core::ConstVector<IPresetHandler::Preset *>;
  // Borrowed lists and entries must outlive their binding. Indexes 7 and 8
  // are observed roster slots whose original enum names are unresolved.
  std::array<const PresetRoster *, 9> presetRosters{};
};

class SLChannelBase;
class MappableMixer;

class MixerClientComponentBase {
public:
  // Independent portable setup; no original constructor/layout credit.
  // Borrowed groups and cached channel must outlive this source-port instance.
  MixerClientComponentBase() = default;
  MixerClientComponentBase(Core::Portable::Component &groups,
                           SLChannelBase *cached = nullptr)
      : channelGroups_(&groups), selectedChannel_(cached) {}
  virtual Core::Portable::Component *getChannelGroup(ChannelType) const;
  ChannelType getChannelGroupType(const Core::Portable::Component &) const;
  SLChannelBase *getSelectedChannel() const;
  void channelSelected(SLChannelBase *);
  // Independent borrowed composition, not original multiple inheritance.
  // Bind the actual observer owner on every mixer used as a master-chain root.
  void bindSourcePortSelectionObservers(MappableMixer &observer) {
    selectionObservers_ = &observer;
  }
  virtual bool isStereoChannelType(ChannelType type) const;
  // Portable int32 return choice. Original spelling/signedness is unresolved.
  virtual std::int32_t getNumGeqs() const;
  virtual std::int32_t getNumMixGeqs() const;
  // Observed 0/1/2 codes; original enum/return spelling is unresolved.
  std::uint32_t getCascadeState() const;
  MixerClientComponentBase *getMasterMixer() const;
  MixerClientComponentBase *getSlaveMixer() const;
  void setMasterMixer(MixerClientComponentBase *mixer);
  // Borrowed list and entries outlive the binding. Rebind after count changes.
  void bindGeqs(const Core::ConstVector<Core::Portable::Component *> *geqs);
  Core::Portable::Component *getMixGeq(int index) const;
  Core::Portable::Component *getMainGeq(bool last) const;
  bool isChannelComponent(Core::Portable::Component *component) const;
  IPresetHandler::PresetType translatePresetType(const char *type) const;
  void getPresetType(IPresetHandler::PresetType type,
                     Core::CStringBuffer<128> &label) const;
  void getSuggestedPresetName(IPresetHandler::PresetType type,
                              Core::CStringBuffer<128> &label) const;
  int getNumPresets(IPresetHandler::PresetType type, const char *name) const;
  IPresetHandler::Preset *getPreset(IPresetHandler::PresetType type, int index,
                                    const char *name) const;
  void getRemotePresetTarget(IPresetHandler::PresetType type,
                             Core::CStringBuffer<256> &target);
  // Releases each unique raw allocation from ::operator new, or null. Records
  // must have no destructor obligation. Borrowed preset rosters are excluded.
  void clearPresets(Core::Vector<IPresetHandler::Preset *> &ownedRecords);
  PortableMixerState &portableState() { return state_; }

private:
  PortableMixerState state_;
  // Independent typed composition, not recovered original offsets/ownership.
  Core::Portable::Component ownedChannelGroups_;
  Core::Portable::Component *channelGroups_ = &ownedChannelGroups_;
  mutable SLChannelBase *selectedChannel_ = nullptr;
  MappableMixer *selectionObservers_ = nullptr;
};

// Original inheritance is not asserted by this portable declaration.
class MixerClientComponent {
public:
  bool isAggregateMeteringChannelType(ChannelType type) const;
};
} // namespace Presonus
