#pragma once

#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include "presonus/surface/MixerPageComponent.hpp"
#include "presonus/surface/SubAssignPageComponent.hpp"
#include <cstdint>

namespace Core::Portable {
class Component;
}

namespace presonus::surface {
// Explicit source-port state. These fields do not describe the ARM object
// layout.
struct GroupsPageState {
  std::int32_t listOffset = 0;
  std::int32_t selection = -1;
  Core::ConstVector<Core::Portable::Parameter *> selectionParameters{nullptr,
                                                                     0};
  Core::ConstVector<Core::Portable::Component *> firstGroups{nullptr, 0};
  Core::ConstVector<Core::Portable::Component *> secondGroups{nullptr, 0};
  Core::Portable::Component *observedGroup = nullptr;
};
// App-specific boundaries remain unresolved; caller must provide them. There
// are no default/no-op production providers. Tests capture calls at this seam.
struct GroupsPageDependencies {
  virtual ~GroupsPageDependencies() = default;
  virtual void refreshList() = 0;
  virtual void doselect() = 0;
  virtual void observeGroup(Core::Portable::Component *) = 0;
};
} // namespace presonus::surface

namespace Presonus::Surface {
// Portable contract, original inheritance/layout and unencoded returns pending.
class GroupsPageComponent : public MixerPageComponent {
public:
  GroupsPageComponent(presonus::surface::GroupsPageState &state,
                      presonus::surface::GroupsPageDependencies &dependencies)
      : state(state), dependencies(dependencies) {}
  ~GroupsPageComponent() override;
  bool isAutoGroup(Core::Portable::Component *) const;
  bool isValidGroup(Core::Portable::Component *) const;
  void select(Core::Portable::Parameter *);
  Core::Portable::Component *getSelectedSlaveGroup() const;
  void addRemoveObservers(Presonus::MixerClientComponentBase *, bool);
  void observeGroup(Core::Portable::Component *);
  void launchEdit();
  void doselect();
  void updateFilter();
  // Independent replay/source-port inspection; not an original ELF interface.
  int sourcePortObservedCount() const { return observedParameters.count(); }
  void updateGroups(Core::Portable::Component *);
  void setMixerComponent(Presonus::MixerClientComponentBase *) override;
  void refreshList();
  void addListOffset(int delta);
  int getMaxListOffset() const;
  void setListOffset(int offset);
  void deSelect();
  void updateSelection();

private:
  Core::Vector<Core::Portable::Parameter *> observedParameters;
  Core::Vector<Core::Portable::Component *> groups[2];
  int previousCounts[2] = {0, 0};
  Presonus::ChannelGroupFilter groupFilters[2] = {
      Presonus::ChannelGroupFilter(39), Presonus::ChannelGroupFilter(32)};
  presonus::surface::GroupsPageState &state;
  presonus::surface::GroupsPageDependencies &dependencies;
};
} // namespace Presonus::Surface
