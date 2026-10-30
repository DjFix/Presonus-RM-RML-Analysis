#pragma once
namespace Presonus::UC {
// Actual app interface RTTI/one pure slot. Chosen void return is provisional;
// original unencoded return declaration is not established by mangling alone.
class IFirmwareUpdateListener {
public:
  virtual void onProgress(const char *message, float progress) = 0;

protected:
  ~IFirmwareUpdateListener() = default;
};
} // namespace Presonus::UC
