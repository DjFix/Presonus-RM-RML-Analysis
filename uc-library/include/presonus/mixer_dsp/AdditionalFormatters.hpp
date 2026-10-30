#pragma once
#include "core/public/coreformatter.h"
namespace Presonus::Dsp {
struct AdditionalFormatterSourceTag {};
class BPMFormatter : public Core::Formatter {
public:
  explicit BPMFormatter(bool label);
  explicit BPMFormatter(AdditionalFormatterSourceTag, bool sourceLabel = false);
  ~BPMFormatter() override;
  // Actual CCL override contracts; original unencoded returns remain
  // unresolved.
  void print(Data &) const override;
  bool scan(Data &) const override;

private:
  bool sourceLabel_;
};
class MillisecondsFormatter : public Core::Formatter {
public:
  MillisecondsFormatter(const char *name, bool highPrecision);
  // Provisional source-port return/static declaration, original spelling
  // pending.
  static MillisecondsFormatter *instance(bool finePrecision);
  explicit MillisecondsFormatter(AdditionalFormatterSourceTag,
                                 bool sourceHighPrecision = false);
  ~MillisecondsFormatter() override;
  // Actual CCL override contracts; original unencoded returns remain
  // unresolved.
  void print(Data &) const override;
  bool scan(Data &) const override;

private:
  bool sourceHighPrecision_;
};
class CounterFormatter : public Core::Formatter {
public:
  explicit CounterFormatter(int width);
  explicit CounterFormatter(AdditionalFormatterSourceTag, int sourceWidth = 1);
  ~CounterFormatter() override;
  // Actual CCL override contracts; original unencoded returns remain
  // unresolved.
  void print(Data &) const override;
  bool scan(Data &) const override;

private:
  int sourceWidth_;
};
class GainFormatter : public Core::Formatter {
public:
  GainFormatter(int precision, bool label);
  // Return pointer/const/static spelling unproved; provisional source port.
  static const char *nameFromPrecision(int precision, bool label);
  explicit GainFormatter(AdditionalFormatterSourceTag, int sourcePrecision = 1,
                         bool sourceLabel = false);
  ~GainFormatter() override;
  // Actual CCL override contracts; original unencoded returns remain
  // unresolved.
  void print(Data &) const override;
  bool scan(Data &) const override;

private:
  int sourcePrecision_;
  bool sourceLabel_;
};
class PanFormatter : public Core::Formatter {
public:
  // Named parameter identity established; enum category/underlying int remain
  // explicit portable choices. Original C1/C2 declarations stay pending.
  enum Mode : int;
  explicit PanFormatter(Mode mode);
  // Return pointer/const/static spelling unproved; provisional source port.
  static const char *nameFromMode(Mode mode);
  explicit PanFormatter(AdditionalFormatterSourceTag, int sourceMode = 0);
  ~PanFormatter() override;
  // Actual CCL override contracts; original unencoded returns remain
  // unresolved.
  void print(Data &) const override;
  bool scan(Data &) const override;

private:
  int sourceMode_;
};
} // namespace Presonus::Dsp
