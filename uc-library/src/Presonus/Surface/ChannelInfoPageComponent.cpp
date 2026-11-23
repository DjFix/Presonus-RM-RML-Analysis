#include "presonus/surface/ChannelInfoPageComponent.hpp"

#include "presonus/utilities/string_utils.hpp"

#include <algorithm>
#include <cstdint>
#include <cstring>
namespace Presonus::Surface {
ChannelInfoPageComponent::~ChannelInfoPageComponent() = default;
void ChannelInfoPageComponent::handleLocalSourceSelect(float value) {
  auto *input = findParameter("dig_in");
  auto *option = findParameter("dig_opt");
  if (!input || !option)
    return;
  input->setValue(value, true);
  if (value > 0.f)
    option->setValue(value - 1.f, true);
}
void ChannelInfoPageComponent::handleExternalSourceSelect() {
  auto *input = findParameter("dig_in");
  auto *option = findParameter("dig_opt");
  if (!input || !option)
    return;
  float value = 0.f;
  if (input->getValue() > 0.f)
    value = option->getValue() + 1.f;
  getParameterByTag(1009)->setValue(value, false);
}

void ChannelInfoPageComponent::bindIconSkinDirectory(
    const Core::Portable::FileName &path) {
  iconSkinDirectory_ = path;
  iconManager_.reset();
}

const IconManager &ChannelInfoPageComponent::iconManager() const {
  if (!iconManager_) {
    auto path = iconSkinDirectory_;
    path.descend("bitmaps").descend("trackicons");
    iconManager_.emplace(path);
    iconManager_->loadIcons();
  }
  return *iconManager_;
}

const IconManager::ChannelCategory *
ChannelInfoPageComponent::selectedIconCategory() const {
  return iconLists_.selectedCategory < 0
             ? nullptr
             : iconManager().getCategory(iconLists_.selectedCategory);
}

int ChannelInfoPageComponent::getMaxListOffset(ListType type) const {
  int count = 0;
  if (type == ListType::Categories) {
    const auto &manager = iconManager();
    // The provider loads only named entries and yields a category with an
    // empty name at the first index beyond the enumerated categories.
    while (!manager.getCategory(count)->name().isEmpty())
      ++count;
  } else if (type == ListType::Icons) {
    if (const auto *category = selectedIconCategory())
      count = category->iconCount();
  }
  return count > 0 ? ((count - 1) / 5) * 5 : 0;
}

void ChannelInfoPageComponent::updateList(ListType type) {
  if (type != ListType::Categories && type != ListType::Icons)
    return;
  const bool categories = type == ListType::Categories;
  const int offset =
      std::min(getMaxListOffset(type),
               categories ? iconLists_.categoryOffset : iconLists_.iconOffset);
  const auto &manager = iconManager();
  const int firstTag = categories ? 100 : 200;
  const int selected =
      categories ? iconLists_.selectedCategory : iconLists_.selectedIcon;
  const auto *category = categories ? nullptr : selectedIconCategory();
  for (int row = 0; row < 5; ++row) {
    auto *label = getParameterByTag(firstTag + 2 * row);
    auto *value = getParameterByTag(firstTag + 2 * row + 1);
    if (!label || !value)
      continue;

    const int index = offset + row;
    Core::CString256 text;
    if (categories) {
      if (const auto *entry = manager.getCategory(index))
        text = entry->name().str();
    } else if (category) {
      text = category->getIconName(index);
    }
    presonus::utilities::makeProperMixedCase(text);
    label->fromString(text, false);
    value->setValue(index == selected ? 1.f : 0.f, false);
  }
}

void ChannelInfoPageComponent::addListOffset(ListType type, int delta) {
  int &offset = type == ListType::Categories ? iconLists_.categoryOffset
                                             : iconLists_.iconOffset;
  const auto candidate = static_cast<std::int64_t>(offset) + delta;
  const int next = candidate < 0 ? 0
                                 : static_cast<int>(std::min<std::int64_t>(
                                       candidate, getMaxListOffset(type)));
  if (next == offset)
    return;
  offset = next;
  updateList(type);
}

void ChannelInfoPageComponent::categoryChanged() {
  iconLists_.selectedIcon = -1;
  iconLists_.iconOffset = 0;
  Core::Portable::FileName icon;
  if (const auto *parameter = findParameter("ch_icon"))
    parameter->toString(icon.getBuffer(), icon.getSize());
  if (!icon.isEmpty()) {
    const auto *category = selectedIconCategory();
    auto parent = icon;
    parent.ascend();
    if (category && (iconLists_.selectedCategory == 0 ||
                     std::strcmp(parent, category->name()) == 0)) {
      icon.getName(icon);
      iconLists_.selectedIcon = category->getIconIndex(icon);
      if (iconLists_.selectedIcon >= 0)
        iconLists_.iconOffset = iconLists_.selectedIcon;
    }
  }
  updateList(ListType::Icons);
}
} // namespace Presonus::Surface
