#pragma once
namespace Presonus::Panel {
class GeqUIComponent;
// Portable source port. Original inheritance, object layout and ordinary return
// declaration are unresolved. Component lifetime is borrowed from the caller.
class GEQPage {
public:
  explicit GEQPage(GeqUIComponent *component = nullptr)
      : component_(component) {}
  void recall();
  GeqUIComponent *portableComponent() const { return component_; }

private:
  GeqUIComponent *component_;
};
} // namespace Presonus::Panel
