"use strict";

export const DEFAULT_MITER_LIMIT = 2;

export function clamp(value, minimum, maximum) {
  if (maximum < minimum) {
    throw new RangeError("clamp requires maximum >= minimum");
  }
  return Math.min(maximum, Math.max(minimum, value));
}

export function smoothstep01(value) {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

export function superellipseRadiusFactor(theta, shape) {
  const t = smoothstep01(shape);
  const exponent = 2 + 2 * t;
  const c = Math.abs(Math.cos(theta));
  const s = Math.abs(Math.sin(theta));
  const denominator =
    Math.pow(
      Math.pow(c, exponent) + Math.pow(s, exponent),
      1 / exponent,
    );
  const diagonalNormaliser = Math.pow(2, 1 / exponent - 0.5);

  return diagonalNormaliser / denominator;
}

export function shapeRadiusFactor(theta, shape) {
  return superellipseRadiusFactor(theta, shape);
}

export function minimumShapeFactor(shape, samples = 1440) {
  let minimum = Number.POSITIVE_INFINITY;

  for (let index = 0; index < samples; index += 1) {
    const theta = (2 * Math.PI * index) / samples;
    minimum = Math.min(minimum, shapeRadiusFactor(theta, shape));
  }

  return minimum;
}

export function basePoint(shape, theta) {
  const factor = shapeRadiusFactor(theta, shape);
  return [
    factor * Math.cos(theta),
    factor * Math.sin(theta),
  ];
}

export function buildArcLengthMap(shape, count) {
  if (!Number.isInteger(count) || count < 4) {
    throw new RangeError("count must be an integer >= 4");
  }

  const basePoints = [];
  for (let index = 0; index < count; index += 1) {
    const theta = (2 * Math.PI * index) / count;
    basePoints.push(basePoint(shape, theta));
  }

  const cumulative = new Array(count).fill(0);
  let total = 0;

  for (let index = 1; index < count; index += 1) {
    const previous = basePoints[index - 1];
    const current = basePoints[index];
    total += Math.hypot(
      current[0] - previous[0],
      current[1] - previous[1],
    );
    cumulative[index] = total;
  }

  const last = basePoints[count - 1];
  const first = basePoints[0];
  total += Math.hypot(first[0] - last[0], first[1] - last[1]);

  return {
    fractions: cumulative.map(function (distance) {
      return distance / total;
    }),
    perimeterFactor: total,
  };
}

function wrap01(value) {
  return ((value % 1) + 1) % 1;
}

function interpolateBasePoint(shape, arcFractions, fraction) {
  const target = wrap01(fraction);
  let low = 0;
  let high = arcFractions.length - 1;

  while (low < high) {
    const mid = Math.floor((low + high + 1) / 2);
    if (arcFractions[mid] <= target) {
      low = mid;
    } else {
      high = mid - 1;
    }
  }

  const index = low;
  const nextIndex = (index + 1) % arcFractions.length;
  const startFraction = arcFractions[index];
  const endFraction =
    nextIndex === 0 ? 1 : arcFractions[nextIndex];
  const span = Math.max(1e-12, endFraction - startFraction);
  const t = (target - startFraction) / span;

  const theta0 = (2 * Math.PI * index) / arcFractions.length;
  const theta1 =
    nextIndex === 0
      ? 2 * Math.PI
      : (2 * Math.PI * nextIndex) / arcFractions.length;
  const p0 = basePoint(shape, theta0);
  const p1 = basePoint(shape, theta1);

  return [
    p0[0] + t * (p1[0] - p0[0]),
    p0[1] + t * (p1[1] - p0[1]),
  ];
}

function normalAtArcFraction(shape, arcFractions, fraction, step) {
  const before = interpolateBasePoint(
    shape,
    arcFractions,
    fraction - step,
  );
  const after = interpolateBasePoint(
    shape,
    arcFractions,
    fraction + step,
  );
  const tx = after[0] - before[0];
  const ty = after[1] - before[1];
  const length = Math.hypot(tx, ty);

  if (length < 1e-12) {
    return [0, 0];
  }

  return [ty / length, -tx / length];
}

export function crenellationWave(phase, crenellationShape = 0.5) {
  const sine = Math.sin(phase);

  if (crenellationShape <= 0.5) {
    // Preserve the original sharper-than-sine end of the control.
    const coefficient = -0.16 * (0.5 - crenellationShape) / 0.25;
    return (sine + coefficient * Math.sin(3 * phase)) / (1 - coefficient);
  }

  // Morph smoothly from sine to a rounded square wave.
  // tanh is odd, so crests and valleys flatten equally:
  // wave(phase + PI) = -wave(phase). Dividing by tanh(steepness)
  // keeps both the crest and valley at exactly +/-1.
  const steepness = 2.6 * (crenellationShape - 0.5) / 0.75;
  return Math.tanh(steepness * sine) / Math.tanh(steepness);
}

export function sampleBoundary(
  radius,
  amplitude,
  waves,
  shape,
  arcFractions,
  crenellationShape = 0.5,
) {
  const waveCount = Math.max(1, Math.round(waves));
  const normalStep = 2 / arcFractions.length;

  return arcFractions.map(function (arcFraction) {
    const base = interpolateBasePoint(shape, arcFractions, arcFraction);
    const normal = normalAtArcFraction(
      shape,
      arcFractions,
      arcFraction,
      normalStep,
    );
    const phase = 2 * Math.PI * waveCount * arcFraction;
    const displacement =
      amplitude * crenellationWave(phase, crenellationShape);

    return [
      radius * base[0] + displacement * normal[0],
      radius * base[1] + displacement * normal[1],
    ];
  });
}

function unitVector(x, y) {
  const length = Math.hypot(x, y);
  if (length < 1e-12) {
    return [0, 0];
  }
  return [x / length, y / length];
}

export function offsetClosedPolyline(
  points,
  distance,
  miterLimit = DEFAULT_MITER_LIMIT,
) {
  if (points.length < 3) {
    throw new RangeError("closed polyline requires at least three points");
  }
  if (miterLimit < 1) {
    throw new RangeError("miterLimit must be >= 1");
  }
  if (distance === 0) {
    return points.map(function (point) {
      return [point[0], point[1]];
    });
  }

  const limit = Math.abs(distance) * miterLimit;

  return points.map(function (current, index) {
    const previous = points[(index - 1 + points.length) % points.length];
    const next = points[(index + 1) % points.length];

    const previousEdge = unitVector(
      current[0] - previous[0],
      current[1] - previous[1],
    );
    const nextEdge = unitVector(
      next[0] - current[0],
      next[1] - current[1],
    );

    const previousNormal = [previousEdge[1], -previousEdge[0]];
    const nextNormal = [nextEdge[1], -nextEdge[0]];
    const miter = unitVector(
      previousNormal[0] + nextNormal[0],
      previousNormal[1] + nextNormal[1],
    );

    let denominator =
      miter[0] * nextNormal[0] + miter[1] * nextNormal[1];

    if (Math.abs(denominator) < 1e-9) {
      denominator = denominator < 0 ? -1e-9 : 1e-9;
    }

    let miterLength = distance / denominator;
    miterLength = Math.max(-limit, Math.min(limit, miterLength));

    return [
      current[0] + miter[0] * miterLength,
      current[1] + miter[1] * miterLength,
    ];
  });
}

export function translatePoints(points, x, y) {
  return points.map(function (point) {
    return [point[0] + x, point[1] + y];
  });
}

export function formatCoordinate(value) {
  return Number(value.toFixed(3)).toString();
}

export function closedPath(points) {
  if (points.length === 0) {
    return "";
  }

  const commands = points.map(function (point, index) {
    const prefix = index === 0 ? "M" : "L";
    return (
      prefix +
      " " +
      formatCoordinate(point[0]) +
      " " +
      formatCoordinate(point[1])
    );
  });

  return commands.join(" ") + " Z";
}

export function ringPath(innerPoints, outerPoints) {
  return (
    closedPath(outerPoints) +
    " " +
    closedPath(innerPoints.slice().reverse())
  );
}
