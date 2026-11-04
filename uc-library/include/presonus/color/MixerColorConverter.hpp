#pragma once
#include "presonus/color/IColorConverter.hpp"
// The original class is in global scope. No ARM layout claim.
class MixerColorConverter : public Presonus::IColorConverter {
public:
  ~MixerColorConverter() override;
  int getColorIndexForRGB(const Core::Color &) const override;
  Core::Color getRGBFromColorIndex(int) const override;
};
