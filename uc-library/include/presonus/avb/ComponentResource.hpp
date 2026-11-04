#pragma once
namespace presonus::avb {
// Explicit external AVB resource boundary; native slot +0x10 is observed.
class ComponentResource {
public:
  virtual ~ComponentResource() = default;
  virtual void release() = 0;
};
} // namespace presonus::avb
