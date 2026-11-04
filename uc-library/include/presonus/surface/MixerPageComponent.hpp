#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/PageComponent.hpp"
#include "presonus/mixer_state/MixerState.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdint>
#include <optional>
namespace Presonus {
class MixerClientComponentBase;
class IMappingController;
} // namespace Presonus
#include "presonus/ChannelGroupFilter.hpp"
namespace presonus::surface {
// Independent application boundary. No original declaration, vtable or layout
// is claimed. Core operations are implemented with the real CCL providers.
struct MixerSelectionView {
  Presonus::ChannelGroupFilter *filter = nullptr;
  Core::Portable::Component *selectedGroup = nullptr;
};
struct MixerPageAccess {
  virtual ~MixerPageAccess() = default;
  virtual Core::Portable::Component *
  groupContainer(Presonus::MixerClientComponentBase *, const char *) = 0;
  virtual Core::Portable::Component *
  channelContainer(Presonus::MixerClientComponentBase *, int) = 0;
  virtual Presonus::MixerClientComponentBase *
  slaveMixer(Presonus::MixerClientComponentBase *) = 0;
  virtual Core::Portable::Component *
  mixerRoot(Presonus::MixerClientComponentBase *) = 0;
  virtual Core::Portable::Component *
  selectedChannel(Presonus::MixerClientComponentBase *) = 0;
  virtual void setFilter(Presonus::MixerClientComponentBase *,
                         Presonus::ChannelGroupFilter *) = 0;
  virtual void setSelectedGroup(Presonus::MixerClientComponentBase *,
                                Core::Portable::Component *) = 0;
};
// Independent borrowed source-port views. These are not original mixer fields,
// inheritance or vtable declarations. Disengaged optionals reject missing
// bindings; an explicitly bound null pointer is a supported absent provider.
struct MixerPageView {
  Presonus::MixerClientComponentBase *identity = nullptr;
  std::optional<Core::Portable::Component *> groupTree;
  std::optional<Core::Portable::Component *> root;
  std::optional<Core::Portable::Component *> channels[8];
  std::optional<Presonus::MixerClientComponentBase *> slave;
  std::optional<Core::Portable::Component *> selected;
  MixerSelectionView *selectionState = nullptr;
};
class BorrowedMixerPageAccess : public MixerPageAccess {
public:
  void registerView(MixerPageView &);
  Core::Portable::Component *
  groupContainer(Presonus::MixerClientComponentBase *, const char *) override;
  Core::Portable::Component *
  channelContainer(Presonus::MixerClientComponentBase *, int) override;
  Presonus::MixerClientComponentBase *
  slaveMixer(Presonus::MixerClientComponentBase *) override;
  Core::Portable::Component *
  mixerRoot(Presonus::MixerClientComponentBase *) override;
  Core::Portable::Component *
  selectedChannel(Presonus::MixerClientComponentBase *) override;

  void setFilter(Presonus::MixerClientComponentBase *,
                 Presonus::ChannelGroupFilter *) override;
  void setSelectedGroup(Presonus::MixerClientComponentBase *,
                        Core::Portable::Component *) override;

private:
  MixerPageView &view(Presonus::MixerClientComponentBase *) const;
  struct RegisteredView {
    Presonus::MixerClientComponentBase *identity;
    MixerPageView *view;
  };
  Core::Vector<RegisteredView> views_;
};
std::int32_t addWrap(std::int32_t, std::int32_t);
} // namespace presonus::surface
namespace Presonus::Surface {
// Portable source model, not ARM object layout or original inheritance proof.
class MixerPageComponent : public Core::Portable::Component {
public:
  explicit MixerPageComponent(
      presonus::surface::MixerPageAccess *access = nullptr,
      Presonus::PageComponent *page = nullptr)
      : access_(access), page_(page) {}
  virtual ~MixerPageComponent();
  virtual void setMixerComponent(Presonus::MixerClientComponentBase *);
  void setMappingController(Presonus::IMappingController *);
  Presonus::MixerClientComponentBase *mixer() const { return mixer_; }
  Presonus::IMappingController *mapping() const { return mapping_; }
  void bindPage(Presonus::PageComponent &page) { page_ = &page; }
  void bindAccess(presonus::surface::MixerPageAccess &access) {
    access_ = &access;
  }

protected:
  presonus::surface::MixerPageAccess &access() const;
  Presonus::MixerClientComponentBase *mixer_ = nullptr;
  Presonus::IMappingController *mapping_ = nullptr;
  presonus::surface::MixerPageAccess *access_;
  Presonus::PageComponent *page_;
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};
} // namespace Presonus::Surface
