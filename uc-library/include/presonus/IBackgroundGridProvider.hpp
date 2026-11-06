#pragma once
namespace Presonus {
// Original secondary virtual-table slots bind Y then X. The modern source
// interface has a safe virtual destructor; this does not reproduce ARM layout.
class IBackgroundGridProvider {
public:
  virtual ~IBackgroundGridProvider() = default;
  virtual int toYGridPixel(float) const = 0;
  virtual int toXGridPixel(float) const = 0;
};
} // namespace Presonus
