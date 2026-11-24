#pragma once
#include "presonus/PageComponent.hpp"
namespace Presonus::Surface {
class PreampsPageComponent : public PageComponent {
public:
  PreampsPageComponent(const char *formName, int tag);
  struct SourcePortConstruction {};
  explicit PreampsPageComponent(SourcePortConstruction)
      : PageComponent("", "", 0) {}
  ~PreampsPageComponent() override;
};
} // namespace Presonus::Surface
