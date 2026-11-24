#pragma once
#include "presonus/MackieControlModel.hpp"
#include "presonus/PageComponent.hpp"
namespace Presonus::Surface {
class AudioUtilitiesPage : public PageComponent {
public:
  AudioUtilitiesPage(const char *formName, int tag);
  AudioUtilitiesPage() : PageComponent("", "", 0) {}
  ~AudioUtilitiesPage() override;
};
} // namespace Presonus::Surface
