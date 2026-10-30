#pragma once

namespace Core {
// Portable storage for the two range fields observed at ARM32 this+4/this+8.
// The leading word, inheritance and vtable ABI are not modeled or recovered.
struct PortableInterpolatorRange {
  float minimum = 0;
  float maximum = 1;
};

class LinearInterpolator {
public:
  float normalizedToRange(float normalized) const;
  float rangeToNormalized(float value) const;
  // Independent access API, not a recovered original method.
  PortableInterpolatorRange &portableRange() { return range_; }

private:
  PortableInterpolatorRange range_;
};

class LinearReverseInterpolator {
public:
  float normalizedToRange(float normalized) const;
  float rangeToNormalized(float value) const;
  PortableInterpolatorRange &portableRange() { return range_; }

private:
  PortableInterpolatorRange range_;
};
} // namespace Core
