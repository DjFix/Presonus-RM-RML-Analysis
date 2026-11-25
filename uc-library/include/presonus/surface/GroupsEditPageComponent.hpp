#pragma once

#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/GroupsPageComponent.hpp"
#include "presonus/surface/MixerPageComponent.hpp"
#include <cstdint>
#include <memory>

namespace Core::Portable {
struct WheelEvent;
}

namespace presonus::surface {
struct GroupsEditState;
struct GroupsEditDependencies;
} // namespace presonus::surface

namespace Presonus::Surface {
// Portable source contract. Original inheritance, layout and unencoded return
// declarations remain unresolved; this class is not an ARM object overlay.
class GroupsEditPageComponent : public MixerPageComponent {
public:
  struct AssignItem {
    Core::Portable::Component *channel = nullptr;
    Core::Portable::Component *group = nullptr;
    int tag = 0;
  };

  GroupsEditPageComponent(
      presonus::surface::GroupsEditState &state,
      presonus::surface::GroupsEditDependencies &dependencies)
      : state(state), dependencies(dependencies) {}
  struct SourcePortConstruction {};
  // Tagged mode owns its state; the existing reference constructor borrows it.
  GroupsEditPageComponent(
      SourcePortConstruction,
      presonus::surface::GroupsEditDependencies &dependencies);
  ~GroupsEditPageComponent() override;
  presonus::surface::GroupsEditState &sourcePortState() { return state; }
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
  void buildItemsList();
  void paramChanged(Core::Portable::Parameter *parameter, int message);
  void updateFilterAssignments();
  int getMaxListOffset() const;
  void textInputFinished(bool accepted);
  void setListOffset(int offset);
  void deleteGroup();
  void addListOffset(int delta);
  void onWheelInput(const Core::Portable::WheelEvent &event);
  void rename();
  void onShow(bool visible);

private:
  std::unique_ptr<presonus::surface::GroupsEditState> ownedState_;
  presonus::surface::GroupsEditState &state;
  presonus::surface::GroupsEditDependencies &dependencies;
};
} // namespace Presonus::Surface

namespace presonus::surface {
struct GroupsEditSelection {
  Presonus::Surface::GroupsPageComponent *page = nullptr;
  Core::Portable::Component *group = nullptr;
  Core::Portable::Component *slaveGroup = nullptr;
};

struct GroupsEditState {
  bool mixerAvailable = false;
  std::int32_t listOffset = 0;
  Core::Vector<Presonus::Surface::GroupsEditPageComponent::AssignItem> items;
  Core::Portable::ParamList parameters;
  Core::Portable::Component *navigation = nullptr;
};

// Required app boundaries, without default production providers. Core
// container, parameter lookup, aliasing, conversion and reset behavior uses
// real CCL.
struct GroupsEditDependencies {
  virtual ~GroupsEditDependencies() = default;
  virtual GroupsEditSelection findGroupsPage() = 0;
  virtual bool hasSlaveMixer() = 0;
  virtual Core::ConstVector<Core::Portable::Component *>
  components(const char *name, bool slave) = 0;
  virtual Core::Portable::Parameter *findParameter(const char *name) = 0;
  virtual void
  startTextInput(Core::Portable::Parameter *parameter, const char *title,
                 Presonus::Surface::GroupsEditPageComponent &callback) = 0;
  virtual void pageOnShow(bool visible) = 0;
  virtual Presonus::PageComponent &page() = 0;
  virtual void connect(const char *path,
                       Core::Portable::Parameter *parameter) = 0;
};
} // namespace presonus::surface
