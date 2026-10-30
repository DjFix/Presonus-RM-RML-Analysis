#pragma once
#include "core/public/coreformatter.h"
namespace Presonus::Dsp {
// Independent source-port construction; original constructors/layout are
// unverified.
struct FormatterSourceTag {};
class TimeFormatter : public Core::Formatter {
public:
  TimeFormatter();
  explicit TimeFormatter(FormatterSourceTag);
  ~TimeFormatter() override;
  // Override returns follow pinned CCL, not an inferred original declaration.
  void print(Data &data) const override;
  bool scan(Data &data) const override;
};
class FreqFormatter : public Core::Formatter {
public:
  explicit FreqFormatter(bool option);
  explicit FreqFormatter(FormatterSourceTag, bool option = false);
  ~FreqFormatter() override;
  // Override returns follow pinned CCL, not an inferred original declaration.
  void print(Data &data) const override;
  bool scan(Data &data) const override;

private:
  bool sourceOption_;
};
class GainDBFormatter : public Core::Formatter {
public:
  explicit GainDBFormatter(bool option);
  explicit GainDBFormatter(FormatterSourceTag, bool option = false);
  ~GainDBFormatter() override;
  // Override returns follow pinned CCL, not an inferred original declaration.
  void print(Data &data) const override;
  bool scan(Data &data) const override;

private:
  bool sourceOption_;
};
class RatioFormatter : public Core::Formatter {
public:
  RatioFormatter();
  explicit RatioFormatter(FormatterSourceTag);
  ~RatioFormatter() override;
  // Override returns follow pinned CCL, not an inferred original declaration.
  void print(Data &data) const override;
  bool scan(Data &data) const override;
};
class EQQFormatter : public Core::Formatter {
public:
  EQQFormatter();
  explicit EQQFormatter(FormatterSourceTag);
  ~EQQFormatter() override;
  // Override returns follow pinned CCL, not an inferred original declaration.
  void print(Data &data) const override;
  bool scan(Data &data) const override;
};
} // namespace Presonus::Dsp
