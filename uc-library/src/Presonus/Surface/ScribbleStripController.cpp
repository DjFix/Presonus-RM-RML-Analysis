#include "presonus/surface/ScribbleStripController.hpp"

#include "presonus/MappingTable.hpp"
#include "presonus/McuVpotControl.hpp"
#include "presonus/PanControl.hpp"
#include "presonus/surface/ControlName.hpp"
#include <memory>

namespace Presonus::Surface {
ScribbleStripController::~ScribbleStripController() = default;

void *ScribbleStripController::castTo(TypeID type) {
  return type == Core::Portable::ViewController::kTypeID
             ? static_cast<Core::Portable::ViewController *>(this)
             : nullptr;
}

Core::Portable::View *ScribbleStripController::createView(const char *type) {
  const Core::ConstString viewType(type);
  if (viewType == "ScribblePanControl") {
    auto view = std::make_unique<PanControl>(Core::Rect{}, nullptr);
    view->setLinkParam(mapping_.getHardwareParameter(
        ControlName("scribble_linked", index_).str()));
    view->setChannelNumberParam(mapping_.getHardwareParameter(
        ControlName("scribble_number", index_).str()));
    return view.release();
  }
  if (viewType == "ScribbleMcuVpotControl") {
    auto view = std::make_unique<McuVpotControl>(Core::Rect{}, nullptr);
    view->setStyleParameter(mapping_.getHardwareParameter(
        ControlName("scribble_style", index_).str()));
    view->setDotParameter(mapping_.getHardwareParameter(
        ControlName("scribble_dot", index_).str()));
    return view.release();
  }
  return nullptr;
}

void *ScribbleStripController::getObjectForView(const char *name,
                                                const char *type) {
  if (Core::ConstString(type) != Core::Portable::kParamType)
    return nullptr;
  if (name && name[0] == '/')
    return root_.getObjectForView(name, type);

  static constexpr struct {
    const char *name;
    const char *prefix;
  } names[] = {
      {"number", "scribble_number"},    {"label", "scribble_label"},
      {"recordEnable", "scribble_arm"}, {"info", "scribble_info"},
      {"pan", "scribble_pan"},          {"encoderInfo", "scribble_encoderInfo"},
      {"leftSide", "scribble_left"},    {"linked", "scribble_linked"},
      {"style", "scribble_style"},      {"dot", "scribble_dot"}};
  for (const auto &entry : names) {
    if (Core::ConstString(name) == entry.name)
      return mapping_.getHardwareParameter(
          ControlName(entry.prefix, index_).str());
  }
  return mapping_.getHardwareParameter("");
}
} // namespace Presonus::Surface
