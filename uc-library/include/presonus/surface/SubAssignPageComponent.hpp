#pragma once
#include "presonus/surface/MixerPageComponent.hpp"
namespace Presonus::Surface {
class SubAssignPageComponent : public MixerPageComponent {
public:
  using MixerPageComponent::MixerPageComponent;
  ~SubAssignPageComponent() override;
  void buildItemsList();
  void updateParams();
  void addListOffset(int);
  int getMaxListOffset() const;
  void setListOffset(int);
  void paramChanged(Core::Portable::Parameter *, int) override;
  int listOffset = 0;
  Core::Vector<Core::Portable::Component *> items;
};
} // namespace Presonus::Surface
