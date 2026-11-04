#include "presonus/IMainScreenPageController.hpp"
#include "presonus/MappingTable.hpp"
#include <algorithm>
#include <stdexcept>
namespace {
presonus::mapping::ColorOperations *colors = nullptr;
presonus::mapping::ColorOperations &colorOperations() {
  if (!colors)
    throw std::logic_error("MappingTable requires ColorOperations");
  return *colors;
}
} // namespace
namespace Presonus {
void MappingTable::setExtendedOperations(
    presonus::mapping::ExtendedOperations &ops) {
  extended_ = &ops;
}
void MappingTable::setColorOperations(presonus::mapping::ColorOperations &ops) {
  colors = &ops;
}
presonus::mapping::ExtendedOperations &MappingTable::extended() const {
  if (!extended_)
    throw std::logic_error("MappingTable requires ExtendedOperations");
  return *extended_;
}
void MappingTable::setControlBlinkMode(const char *name, const char *mode) {
  if (auto *item = findItem(name))
    extended().blink(*item, mode);
}
int MappingTable::mapColor(const Core::Color &color) {
  return colorOperations().map(color);
}
Core::Color MappingTable::mapColor(const char *name) {
  return colorOperations().map(name);
}
void MappingTable::addMainScreenPage(IMainScreenPageController *page) {
  if (pageCount_ < 128)
    pages_[pageCount_++] = page;
}
IMainScreenPageController *MappingTable::findPage(const char *name) const {
  for (int i = 0; i < pageCount_; ++i) {
    auto *page = pages_[i];
    const char *other = typedPageControllers_ ? page->getPageName()
                                              : extended().pageName(*page);
    if (std::strcmp(name ? name : "", other ? other : "") == 0)
      return page;
  }
  return nullptr;
}
void MappingTable::setPanelControl(const char *name, Panel::Control *control,
                                   const char *mode) {
  if (auto *item = findItem(name)) {
    auto &ops = extended();
    auto *parameter = ops.parameter(*item);
    int translated = ops.translateMode(mode);
    ops.bind(*control, parameter, translated);
    ops.control(*item, control);
  }
}
void MappingTable::connectAltParameter(const char *name,
                                       Core::Portable::Parameter *parameter) {
  if (auto *item = findItem(name)) {
    auto &ops = extended();
    if (auto *control = ops.control(*item)) {
      auto *alias =
          Core::Portable::AliasParam::cast(ops.alternate(*control, false));
      if (alias) {
        if (alias != parameter)
          alias->setOriginal(parameter);
      } else
        ops.alternate(*control, parameter, false);
    }
  }
}
void MappingTable::connectTertiaryParameter(
    const char *name, Core::Portable::Parameter *parameter) {
  if (auto *item = findItem(name)) {
    auto &ops = extended();
    if (auto *control = ops.control(*item)) {
      auto *alias =
          Core::Portable::AliasParam::cast(ops.alternate(*control, true));
      if (alias) {
        if (alias != parameter)
          alias->setOriginal(parameter);
      } else
        ops.alternate(*control, parameter, true);
    }
  }
}
void MappingTable::setControlColor(const char *name, const char *color) {
  if (auto *item = findItem(name)) {
    auto &ops = extended();
    if (auto *control = ops.control(*item)) {
      if (ops.hasLED(*control)) {
        const char *value = color ? color : "";
        if (std::strcmp(value, "default") == 0)
          value = ops.defaultColor(*item);
        ops.color(*control, colorOperations().enumFromString(value, 17));
      }
    }
  }
}
void MappingTable::setControlDefaultColor(const char *name, const char *color,
                                          bool apply) {
  if (auto *item = findItem(name)) {
    if (!color)
      return;
    auto &ops = extended();
    char buffer[32];
    auto length = std::min<std::size_t>(31, std::strlen(color));
    std::memcpy(buffer, color, length);
    buffer[length] = 0;
    ops.defaultColor(*item, buffer);
    if (apply) {
      if (auto *control = ops.control(*item)) {
        if (ops.hasLED(*control)) {
          const char *value = std::strcmp(color, "default") == 0
                                  ? ops.defaultColor(*item)
                                  : color;
          ops.color(*control, colorOperations().enumFromString(value, 17));
        }
      }
    }
  }
}
} // namespace Presonus
