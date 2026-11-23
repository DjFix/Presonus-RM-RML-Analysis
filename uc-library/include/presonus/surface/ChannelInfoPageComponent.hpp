#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/IconManager.hpp"
#include <optional>
namespace Presonus::Surface {
// Actual pinned provider inheritance is an intentional source port, not proof
// of original complete inheritance/layout or ordinary return declarations.
class ChannelInfoPageComponent : public Core::Portable::Component {
public:
  using Component::Component;
  ~ChannelInfoPageComponent() override;
  // Independent source-port binding: vector owns storage, never pointees.
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
  enum class ListType { Categories = 0, Icons = 1 };
  int getMaxListOffset(ListType) const;
  void updateList(ListType);
  void addListOffset(ListType, int);
  void categoryChanged();

  // Independent portable setup for caller-owned skin directories and list
  // state.
  void bindIconSkinDirectory(const Core::Portable::FileName &);
  struct IconListState {
    int categoryOffset = 0;
    int iconOffset = 0;
    int selectedCategory = -1;
    int selectedIcon = -1;
  };
  IconListState &sourcePortIconLists() { return iconLists_; }

  void handleLocalSourceSelect(float value);
  void handleExternalSourceSelect();

private:
  const IconManager &iconManager() const;
  const IconManager::ChannelCategory *selectedIconCategory() const;

  Core::Vector<Core::Portable::AliasParam *> aliases_;
  Core::Portable::FileName iconSkinDirectory_{"/media/skin"};
  mutable std::optional<IconManager> iconManager_;
  IconListState iconLists_;
};
} // namespace Presonus::Surface
