#pragma once

#include "presonus/uc/ClientComponent.hpp"

namespace Presonus {

class DAWDeviceFolder;

// Shared portable implementation of the recovered channel behavior.
// The original ARM object layout and remaining DAW channel behavior are outside
// this interface.
class DAWChannel : public UC::ClientComponent {
public:
  DAWChannel();
  ~DAWChannel() override;

  void *castTo(int typeId) override;
  static void operator delete(void *allocation) noexcept;

  // Initializes a newly assembled channel and its device folders.
  void init(bool removeControls);

  DAWDeviceFolder *getInserts() const;
  DAWDeviceFolder *getCueMixes() const;
  DAWDeviceFolder *getPosts() const;
  DAWDeviceFolder *getSends() const;
  bool isSelected() const;

  // The portable return points into a buffer shared by channel instances.
  // A later formatting call can replace its contents.
  const char *getID() const;

protected:
  static constexpr int selectedCache = 0;
  static constexpr int channelStateCache = 1;
  static constexpr int idCache = 2;

  Core::Portable::Parameter *cachedParameters_[3]{};
};

} // namespace Presonus
