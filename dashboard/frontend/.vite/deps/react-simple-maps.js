import {
  identity,
  select_default,
  zoom_default
} from "./chunk-VYPTL5KB.js";
import {
  Adder,
  merge,
  range
} from "./chunk-V5QLQQ7E.js";
import {
  __export,
  __toESM,
  require_react
} from "./chunk-JRE55LYH.js";

// node_modules/react-simple-maps/dist/shared/JKVre3Xc.es.js
var import_react = __toESM(require_react());

// node_modules/d3-geo/src/index.js
var src_exports = {};
__export(src_exports, {
  geoAlbers: () => albers_default,
  geoAlbersUsa: () => albersUsa_default,
  geoArea: () => area_default,
  geoAzimuthalEqualArea: () => azimuthalEqualArea_default,
  geoAzimuthalEqualAreaRaw: () => azimuthalEqualAreaRaw,
  geoAzimuthalEquidistant: () => azimuthalEquidistant_default,
  geoAzimuthalEquidistantRaw: () => azimuthalEquidistantRaw,
  geoBounds: () => bounds_default,
  geoCentroid: () => centroid_default,
  geoCircle: () => circle_default,
  geoClipAntimeridian: () => antimeridian_default,
  geoClipCircle: () => circle_default2,
  geoClipExtent: () => extent_default,
  geoClipRectangle: () => clipRectangle,
  geoConicConformal: () => conicConformal_default,
  geoConicConformalRaw: () => conicConformalRaw,
  geoConicEqualArea: () => conicEqualArea_default,
  geoConicEqualAreaRaw: () => conicEqualAreaRaw,
  geoConicEquidistant: () => conicEquidistant_default,
  geoConicEquidistantRaw: () => conicEquidistantRaw,
  geoContains: () => contains_default,
  geoDistance: () => distance_default,
  geoEqualEarth: () => equalEarth_default,
  geoEqualEarthRaw: () => equalEarthRaw,
  geoEquirectangular: () => equirectangular_default,
  geoEquirectangularRaw: () => equirectangularRaw,
  geoGnomonic: () => gnomonic_default,
  geoGnomonicRaw: () => gnomonicRaw,
  geoGraticule: () => graticule,
  geoGraticule10: () => graticule10,
  geoIdentity: () => identity_default2,
  geoInterpolate: () => interpolate_default,
  geoLength: () => length_default,
  geoMercator: () => mercator_default,
  geoMercatorRaw: () => mercatorRaw,
  geoNaturalEarth1: () => naturalEarth1_default,
  geoNaturalEarth1Raw: () => naturalEarth1Raw,
  geoOrthographic: () => orthographic_default,
  geoOrthographicRaw: () => orthographicRaw,
  geoPath: () => path_default,
  geoProjection: () => projection,
  geoProjectionMutator: () => projectionMutator,
  geoRotation: () => rotation_default,
  geoStereographic: () => stereographic_default,
  geoStereographicRaw: () => stereographicRaw,
  geoStream: () => stream_default,
  geoTransform: () => transform_default,
  geoTransverseMercator: () => transverseMercator_default,
  geoTransverseMercatorRaw: () => transverseMercatorRaw
});

// node_modules/d3-geo/src/math.js
var epsilon = 1e-6;
var epsilon2 = 1e-12;
var pi = Math.PI;
var halfPi = pi / 2;
var quarterPi = pi / 4;
var tau = pi * 2;
var degrees = 180 / pi;
var radians = pi / 180;
var abs = Math.abs;
var atan = Math.atan;
var atan2 = Math.atan2;
var cos = Math.cos;
var ceil = Math.ceil;
var exp = Math.exp;
var hypot = Math.hypot;
var log = Math.log;
var pow = Math.pow;
var sin = Math.sin;
var sign = Math.sign || function(x3) {
  return x3 > 0 ? 1 : x3 < 0 ? -1 : 0;
};
var sqrt = Math.sqrt;
var tan = Math.tan;
function acos(x3) {
  return x3 > 1 ? 0 : x3 < -1 ? pi : Math.acos(x3);
}
function asin(x3) {
  return x3 > 1 ? halfPi : x3 < -1 ? -halfPi : Math.asin(x3);
}
function haversin(x3) {
  return (x3 = sin(x3 / 2)) * x3;
}

// node_modules/d3-geo/src/noop.js
function noop() {
}

// node_modules/d3-geo/src/stream.js
function streamGeometry(geometry, stream) {
  if (geometry && streamGeometryType.hasOwnProperty(geometry.type)) {
    streamGeometryType[geometry.type](geometry, stream);
  }
}
var streamObjectType = {
  Feature: function(object3, stream) {
    streamGeometry(object3.geometry, stream);
  },
  FeatureCollection: function(object3, stream) {
    var features = object3.features, i2 = -1, n3 = features.length;
    while (++i2 < n3) streamGeometry(features[i2].geometry, stream);
  }
};
var streamGeometryType = {
  Sphere: function(object3, stream) {
    stream.sphere();
  },
  Point: function(object3, stream) {
    object3 = object3.coordinates;
    stream.point(object3[0], object3[1], object3[2]);
  },
  MultiPoint: function(object3, stream) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) object3 = coordinates2[i2], stream.point(object3[0], object3[1], object3[2]);
  },
  LineString: function(object3, stream) {
    streamLine(object3.coordinates, stream, 0);
  },
  MultiLineString: function(object3, stream) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) streamLine(coordinates2[i2], stream, 0);
  },
  Polygon: function(object3, stream) {
    streamPolygon(object3.coordinates, stream);
  },
  MultiPolygon: function(object3, stream) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) streamPolygon(coordinates2[i2], stream);
  },
  GeometryCollection: function(object3, stream) {
    var geometries = object3.geometries, i2 = -1, n3 = geometries.length;
    while (++i2 < n3) streamGeometry(geometries[i2], stream);
  }
};
function streamLine(coordinates2, stream, closed) {
  var i2 = -1, n3 = coordinates2.length - closed, coordinate;
  stream.lineStart();
  while (++i2 < n3) coordinate = coordinates2[i2], stream.point(coordinate[0], coordinate[1], coordinate[2]);
  stream.lineEnd();
}
function streamPolygon(coordinates2, stream) {
  var i2 = -1, n3 = coordinates2.length;
  stream.polygonStart();
  while (++i2 < n3) streamLine(coordinates2[i2], stream, 1);
  stream.polygonEnd();
}
function stream_default(object3, stream) {
  if (object3 && streamObjectType.hasOwnProperty(object3.type)) {
    streamObjectType[object3.type](object3, stream);
  } else {
    streamGeometry(object3, stream);
  }
}

// node_modules/d3-geo/src/area.js
var areaRingSum = new Adder();
var areaSum = new Adder();
var lambda00;
var phi00;
var lambda0;
var cosPhi0;
var sinPhi0;
var areaStream = {
  point: noop,
  lineStart: noop,
  lineEnd: noop,
  polygonStart: function() {
    areaRingSum = new Adder();
    areaStream.lineStart = areaRingStart;
    areaStream.lineEnd = areaRingEnd;
  },
  polygonEnd: function() {
    var areaRing = +areaRingSum;
    areaSum.add(areaRing < 0 ? tau + areaRing : areaRing);
    this.lineStart = this.lineEnd = this.point = noop;
  },
  sphere: function() {
    areaSum.add(tau);
  }
};
function areaRingStart() {
  areaStream.point = areaPointFirst;
}
function areaRingEnd() {
  areaPoint(lambda00, phi00);
}
function areaPointFirst(lambda, phi) {
  areaStream.point = areaPoint;
  lambda00 = lambda, phi00 = phi;
  lambda *= radians, phi *= radians;
  lambda0 = lambda, cosPhi0 = cos(phi = phi / 2 + quarterPi), sinPhi0 = sin(phi);
}
function areaPoint(lambda, phi) {
  lambda *= radians, phi *= radians;
  phi = phi / 2 + quarterPi;
  var dLambda = lambda - lambda0, sdLambda = dLambda >= 0 ? 1 : -1, adLambda = sdLambda * dLambda, cosPhi = cos(phi), sinPhi = sin(phi), k3 = sinPhi0 * sinPhi, u = cosPhi0 * cosPhi + k3 * cos(adLambda), v3 = k3 * sdLambda * sin(adLambda);
  areaRingSum.add(atan2(v3, u));
  lambda0 = lambda, cosPhi0 = cosPhi, sinPhi0 = sinPhi;
}
function area_default(object3) {
  areaSum = new Adder();
  stream_default(object3, areaStream);
  return areaSum * 2;
}

// node_modules/d3-geo/src/cartesian.js
function spherical(cartesian2) {
  return [atan2(cartesian2[1], cartesian2[0]), asin(cartesian2[2])];
}
function cartesian(spherical2) {
  var lambda = spherical2[0], phi = spherical2[1], cosPhi = cos(phi);
  return [cosPhi * cos(lambda), cosPhi * sin(lambda), sin(phi)];
}
function cartesianDot(a3, b2) {
  return a3[0] * b2[0] + a3[1] * b2[1] + a3[2] * b2[2];
}
function cartesianCross(a3, b2) {
  return [a3[1] * b2[2] - a3[2] * b2[1], a3[2] * b2[0] - a3[0] * b2[2], a3[0] * b2[1] - a3[1] * b2[0]];
}
function cartesianAddInPlace(a3, b2) {
  a3[0] += b2[0], a3[1] += b2[1], a3[2] += b2[2];
}
function cartesianScale(vector, k3) {
  return [vector[0] * k3, vector[1] * k3, vector[2] * k3];
}
function cartesianNormalizeInPlace(d3) {
  var l3 = sqrt(d3[0] * d3[0] + d3[1] * d3[1] + d3[2] * d3[2]);
  d3[0] /= l3, d3[1] /= l3, d3[2] /= l3;
}

// node_modules/d3-geo/src/bounds.js
var lambda02;
var phi0;
var lambda1;
var phi1;
var lambda2;
var lambda002;
var phi002;
var p0;
var deltaSum;
var ranges;
var range2;
var boundsStream = {
  point: boundsPoint,
  lineStart: boundsLineStart,
  lineEnd: boundsLineEnd,
  polygonStart: function() {
    boundsStream.point = boundsRingPoint;
    boundsStream.lineStart = boundsRingStart;
    boundsStream.lineEnd = boundsRingEnd;
    deltaSum = new Adder();
    areaStream.polygonStart();
  },
  polygonEnd: function() {
    areaStream.polygonEnd();
    boundsStream.point = boundsPoint;
    boundsStream.lineStart = boundsLineStart;
    boundsStream.lineEnd = boundsLineEnd;
    if (areaRingSum < 0) lambda02 = -(lambda1 = 180), phi0 = -(phi1 = 90);
    else if (deltaSum > epsilon) phi1 = 90;
    else if (deltaSum < -epsilon) phi0 = -90;
    range2[0] = lambda02, range2[1] = lambda1;
  },
  sphere: function() {
    lambda02 = -(lambda1 = 180), phi0 = -(phi1 = 90);
  }
};
function boundsPoint(lambda, phi) {
  ranges.push(range2 = [lambda02 = lambda, lambda1 = lambda]);
  if (phi < phi0) phi0 = phi;
  if (phi > phi1) phi1 = phi;
}
function linePoint(lambda, phi) {
  var p = cartesian([lambda * radians, phi * radians]);
  if (p0) {
    var normal = cartesianCross(p0, p), equatorial = [normal[1], -normal[0], 0], inflection = cartesianCross(equatorial, normal);
    cartesianNormalizeInPlace(inflection);
    inflection = spherical(inflection);
    var delta = lambda - lambda2, sign2 = delta > 0 ? 1 : -1, lambdai = inflection[0] * degrees * sign2, phii, antimeridian = abs(delta) > 180;
    if (antimeridian ^ (sign2 * lambda2 < lambdai && lambdai < sign2 * lambda)) {
      phii = inflection[1] * degrees;
      if (phii > phi1) phi1 = phii;
    } else if (lambdai = (lambdai + 360) % 360 - 180, antimeridian ^ (sign2 * lambda2 < lambdai && lambdai < sign2 * lambda)) {
      phii = -inflection[1] * degrees;
      if (phii < phi0) phi0 = phii;
    } else {
      if (phi < phi0) phi0 = phi;
      if (phi > phi1) phi1 = phi;
    }
    if (antimeridian) {
      if (lambda < lambda2) {
        if (angle(lambda02, lambda) > angle(lambda02, lambda1)) lambda1 = lambda;
      } else {
        if (angle(lambda, lambda1) > angle(lambda02, lambda1)) lambda02 = lambda;
      }
    } else {
      if (lambda1 >= lambda02) {
        if (lambda < lambda02) lambda02 = lambda;
        if (lambda > lambda1) lambda1 = lambda;
      } else {
        if (lambda > lambda2) {
          if (angle(lambda02, lambda) > angle(lambda02, lambda1)) lambda1 = lambda;
        } else {
          if (angle(lambda, lambda1) > angle(lambda02, lambda1)) lambda02 = lambda;
        }
      }
    }
  } else {
    ranges.push(range2 = [lambda02 = lambda, lambda1 = lambda]);
  }
  if (phi < phi0) phi0 = phi;
  if (phi > phi1) phi1 = phi;
  p0 = p, lambda2 = lambda;
}
function boundsLineStart() {
  boundsStream.point = linePoint;
}
function boundsLineEnd() {
  range2[0] = lambda02, range2[1] = lambda1;
  boundsStream.point = boundsPoint;
  p0 = null;
}
function boundsRingPoint(lambda, phi) {
  if (p0) {
    var delta = lambda - lambda2;
    deltaSum.add(abs(delta) > 180 ? delta + (delta > 0 ? 360 : -360) : delta);
  } else {
    lambda002 = lambda, phi002 = phi;
  }
  areaStream.point(lambda, phi);
  linePoint(lambda, phi);
}
function boundsRingStart() {
  areaStream.lineStart();
}
function boundsRingEnd() {
  boundsRingPoint(lambda002, phi002);
  areaStream.lineEnd();
  if (abs(deltaSum) > epsilon) lambda02 = -(lambda1 = 180);
  range2[0] = lambda02, range2[1] = lambda1;
  p0 = null;
}
function angle(lambda04, lambda12) {
  return (lambda12 -= lambda04) < 0 ? lambda12 + 360 : lambda12;
}
function rangeCompare(a3, b2) {
  return a3[0] - b2[0];
}
function rangeContains(range3, x3) {
  return range3[0] <= range3[1] ? range3[0] <= x3 && x3 <= range3[1] : x3 < range3[0] || range3[1] < x3;
}
function bounds_default(feature2) {
  var i2, n3, a3, b2, merged, deltaMax, delta;
  phi1 = lambda1 = -(lambda02 = phi0 = Infinity);
  ranges = [];
  stream_default(feature2, boundsStream);
  if (n3 = ranges.length) {
    ranges.sort(rangeCompare);
    for (i2 = 1, a3 = ranges[0], merged = [a3]; i2 < n3; ++i2) {
      b2 = ranges[i2];
      if (rangeContains(a3, b2[0]) || rangeContains(a3, b2[1])) {
        if (angle(a3[0], b2[1]) > angle(a3[0], a3[1])) a3[1] = b2[1];
        if (angle(b2[0], a3[1]) > angle(a3[0], a3[1])) a3[0] = b2[0];
      } else {
        merged.push(a3 = b2);
      }
    }
    for (deltaMax = -Infinity, n3 = merged.length - 1, i2 = 0, a3 = merged[n3]; i2 <= n3; a3 = b2, ++i2) {
      b2 = merged[i2];
      if ((delta = angle(a3[1], b2[0])) > deltaMax) deltaMax = delta, lambda02 = b2[0], lambda1 = a3[1];
    }
  }
  ranges = range2 = null;
  return lambda02 === Infinity || phi0 === Infinity ? [[NaN, NaN], [NaN, NaN]] : [[lambda02, phi0], [lambda1, phi1]];
}

// node_modules/d3-geo/src/centroid.js
var W0;
var W1;
var X0;
var Y0;
var Z0;
var X1;
var Y1;
var Z1;
var X2;
var Y2;
var Z2;
var lambda003;
var phi003;
var x0;
var y0;
var z0;
var centroidStream = {
  sphere: noop,
  point: centroidPoint,
  lineStart: centroidLineStart,
  lineEnd: centroidLineEnd,
  polygonStart: function() {
    centroidStream.lineStart = centroidRingStart;
    centroidStream.lineEnd = centroidRingEnd;
  },
  polygonEnd: function() {
    centroidStream.lineStart = centroidLineStart;
    centroidStream.lineEnd = centroidLineEnd;
  }
};
function centroidPoint(lambda, phi) {
  lambda *= radians, phi *= radians;
  var cosPhi = cos(phi);
  centroidPointCartesian(cosPhi * cos(lambda), cosPhi * sin(lambda), sin(phi));
}
function centroidPointCartesian(x3, y3, z) {
  ++W0;
  X0 += (x3 - X0) / W0;
  Y0 += (y3 - Y0) / W0;
  Z0 += (z - Z0) / W0;
}
function centroidLineStart() {
  centroidStream.point = centroidLinePointFirst;
}
function centroidLinePointFirst(lambda, phi) {
  lambda *= radians, phi *= radians;
  var cosPhi = cos(phi);
  x0 = cosPhi * cos(lambda);
  y0 = cosPhi * sin(lambda);
  z0 = sin(phi);
  centroidStream.point = centroidLinePoint;
  centroidPointCartesian(x0, y0, z0);
}
function centroidLinePoint(lambda, phi) {
  lambda *= radians, phi *= radians;
  var cosPhi = cos(phi), x3 = cosPhi * cos(lambda), y3 = cosPhi * sin(lambda), z = sin(phi), w2 = atan2(sqrt((w2 = y0 * z - z0 * y3) * w2 + (w2 = z0 * x3 - x0 * z) * w2 + (w2 = x0 * y3 - y0 * x3) * w2), x0 * x3 + y0 * y3 + z0 * z);
  W1 += w2;
  X1 += w2 * (x0 + (x0 = x3));
  Y1 += w2 * (y0 + (y0 = y3));
  Z1 += w2 * (z0 + (z0 = z));
  centroidPointCartesian(x0, y0, z0);
}
function centroidLineEnd() {
  centroidStream.point = centroidPoint;
}
function centroidRingStart() {
  centroidStream.point = centroidRingPointFirst;
}
function centroidRingEnd() {
  centroidRingPoint(lambda003, phi003);
  centroidStream.point = centroidPoint;
}
function centroidRingPointFirst(lambda, phi) {
  lambda003 = lambda, phi003 = phi;
  lambda *= radians, phi *= radians;
  centroidStream.point = centroidRingPoint;
  var cosPhi = cos(phi);
  x0 = cosPhi * cos(lambda);
  y0 = cosPhi * sin(lambda);
  z0 = sin(phi);
  centroidPointCartesian(x0, y0, z0);
}
function centroidRingPoint(lambda, phi) {
  lambda *= radians, phi *= radians;
  var cosPhi = cos(phi), x3 = cosPhi * cos(lambda), y3 = cosPhi * sin(lambda), z = sin(phi), cx = y0 * z - z0 * y3, cy = z0 * x3 - x0 * z, cz = x0 * y3 - y0 * x3, m = hypot(cx, cy, cz), w2 = asin(m), v3 = m && -w2 / m;
  X2.add(v3 * cx);
  Y2.add(v3 * cy);
  Z2.add(v3 * cz);
  W1 += w2;
  X1 += w2 * (x0 + (x0 = x3));
  Y1 += w2 * (y0 + (y0 = y3));
  Z1 += w2 * (z0 + (z0 = z));
  centroidPointCartesian(x0, y0, z0);
}
function centroid_default(object3) {
  W0 = W1 = X0 = Y0 = Z0 = X1 = Y1 = Z1 = 0;
  X2 = new Adder();
  Y2 = new Adder();
  Z2 = new Adder();
  stream_default(object3, centroidStream);
  var x3 = +X2, y3 = +Y2, z = +Z2, m = hypot(x3, y3, z);
  if (m < epsilon2) {
    x3 = X1, y3 = Y1, z = Z1;
    if (W1 < epsilon) x3 = X0, y3 = Y0, z = Z0;
    m = hypot(x3, y3, z);
    if (m < epsilon2) return [NaN, NaN];
  }
  return [atan2(y3, x3) * degrees, asin(z / m) * degrees];
}

// node_modules/d3-geo/src/constant.js
function constant_default(x3) {
  return function() {
    return x3;
  };
}

// node_modules/d3-geo/src/compose.js
function compose_default(a3, b2) {
  function compose(x3, y3) {
    return x3 = a3(x3, y3), b2(x3[0], x3[1]);
  }
  if (a3.invert && b2.invert) compose.invert = function(x3, y3) {
    return x3 = b2.invert(x3, y3), x3 && a3.invert(x3[0], x3[1]);
  };
  return compose;
}

// node_modules/d3-geo/src/rotation.js
function rotationIdentity(lambda, phi) {
  if (abs(lambda) > pi) lambda -= Math.round(lambda / tau) * tau;
  return [lambda, phi];
}
rotationIdentity.invert = rotationIdentity;
function rotateRadians(deltaLambda, deltaPhi, deltaGamma) {
  return (deltaLambda %= tau) ? deltaPhi || deltaGamma ? compose_default(rotationLambda(deltaLambda), rotationPhiGamma(deltaPhi, deltaGamma)) : rotationLambda(deltaLambda) : deltaPhi || deltaGamma ? rotationPhiGamma(deltaPhi, deltaGamma) : rotationIdentity;
}
function forwardRotationLambda(deltaLambda) {
  return function(lambda, phi) {
    lambda += deltaLambda;
    if (abs(lambda) > pi) lambda -= Math.round(lambda / tau) * tau;
    return [lambda, phi];
  };
}
function rotationLambda(deltaLambda) {
  var rotation = forwardRotationLambda(deltaLambda);
  rotation.invert = forwardRotationLambda(-deltaLambda);
  return rotation;
}
function rotationPhiGamma(deltaPhi, deltaGamma) {
  var cosDeltaPhi = cos(deltaPhi), sinDeltaPhi = sin(deltaPhi), cosDeltaGamma = cos(deltaGamma), sinDeltaGamma = sin(deltaGamma);
  function rotation(lambda, phi) {
    var cosPhi = cos(phi), x3 = cos(lambda) * cosPhi, y3 = sin(lambda) * cosPhi, z = sin(phi), k3 = z * cosDeltaPhi + x3 * sinDeltaPhi;
    return [
      atan2(y3 * cosDeltaGamma - k3 * sinDeltaGamma, x3 * cosDeltaPhi - z * sinDeltaPhi),
      asin(k3 * cosDeltaGamma + y3 * sinDeltaGamma)
    ];
  }
  rotation.invert = function(lambda, phi) {
    var cosPhi = cos(phi), x3 = cos(lambda) * cosPhi, y3 = sin(lambda) * cosPhi, z = sin(phi), k3 = z * cosDeltaGamma - y3 * sinDeltaGamma;
    return [
      atan2(y3 * cosDeltaGamma + z * sinDeltaGamma, x3 * cosDeltaPhi + k3 * sinDeltaPhi),
      asin(k3 * cosDeltaPhi - x3 * sinDeltaPhi)
    ];
  };
  return rotation;
}
function rotation_default(rotate) {
  rotate = rotateRadians(rotate[0] * radians, rotate[1] * radians, rotate.length > 2 ? rotate[2] * radians : 0);
  function forward(coordinates2) {
    coordinates2 = rotate(coordinates2[0] * radians, coordinates2[1] * radians);
    return coordinates2[0] *= degrees, coordinates2[1] *= degrees, coordinates2;
  }
  forward.invert = function(coordinates2) {
    coordinates2 = rotate.invert(coordinates2[0] * radians, coordinates2[1] * radians);
    return coordinates2[0] *= degrees, coordinates2[1] *= degrees, coordinates2;
  };
  return forward;
}

// node_modules/d3-geo/src/circle.js
function circleStream(stream, radius, delta, direction, t0, t1) {
  if (!delta) return;
  var cosRadius = cos(radius), sinRadius = sin(radius), step = direction * delta;
  if (t0 == null) {
    t0 = radius + direction * tau;
    t1 = radius - step / 2;
  } else {
    t0 = circleRadius(cosRadius, t0);
    t1 = circleRadius(cosRadius, t1);
    if (direction > 0 ? t0 < t1 : t0 > t1) t0 += direction * tau;
  }
  for (var point, t3 = t0; direction > 0 ? t3 > t1 : t3 < t1; t3 -= step) {
    point = spherical([cosRadius, -sinRadius * cos(t3), -sinRadius * sin(t3)]);
    stream.point(point[0], point[1]);
  }
}
function circleRadius(cosRadius, point) {
  point = cartesian(point), point[0] -= cosRadius;
  cartesianNormalizeInPlace(point);
  var radius = acos(-point[1]);
  return ((-point[2] < 0 ? -radius : radius) + tau - epsilon) % tau;
}
function circle_default() {
  var center = constant_default([0, 0]), radius = constant_default(90), precision = constant_default(2), ring, rotate, stream = { point };
  function point(x3, y3) {
    ring.push(x3 = rotate(x3, y3));
    x3[0] *= degrees, x3[1] *= degrees;
  }
  function circle() {
    var c3 = center.apply(this, arguments), r3 = radius.apply(this, arguments) * radians, p = precision.apply(this, arguments) * radians;
    ring = [];
    rotate = rotateRadians(-c3[0] * radians, -c3[1] * radians, 0).invert;
    circleStream(stream, r3, p, 1);
    c3 = { type: "Polygon", coordinates: [ring] };
    ring = rotate = null;
    return c3;
  }
  circle.center = function(_) {
    return arguments.length ? (center = typeof _ === "function" ? _ : constant_default([+_[0], +_[1]]), circle) : center;
  };
  circle.radius = function(_) {
    return arguments.length ? (radius = typeof _ === "function" ? _ : constant_default(+_), circle) : radius;
  };
  circle.precision = function(_) {
    return arguments.length ? (precision = typeof _ === "function" ? _ : constant_default(+_), circle) : precision;
  };
  return circle;
}

// node_modules/d3-geo/src/clip/buffer.js
function buffer_default() {
  var lines = [], line;
  return {
    point: function(x3, y3, m) {
      line.push([x3, y3, m]);
    },
    lineStart: function() {
      lines.push(line = []);
    },
    lineEnd: noop,
    rejoin: function() {
      if (lines.length > 1) lines.push(lines.pop().concat(lines.shift()));
    },
    result: function() {
      var result = lines;
      lines = [];
      line = null;
      return result;
    }
  };
}

// node_modules/d3-geo/src/pointEqual.js
function pointEqual_default(a3, b2) {
  return abs(a3[0] - b2[0]) < epsilon && abs(a3[1] - b2[1]) < epsilon;
}

// node_modules/d3-geo/src/clip/rejoin.js
function Intersection(point, points, other, entry) {
  this.x = point;
  this.z = points;
  this.o = other;
  this.e = entry;
  this.v = false;
  this.n = this.p = null;
}
function rejoin_default(segments, compareIntersection2, startInside, interpolate, stream) {
  var subject = [], clip = [], i2, n3;
  segments.forEach(function(segment) {
    if ((n4 = segment.length - 1) <= 0) return;
    var n4, p02 = segment[0], p1 = segment[n4], x3;
    if (pointEqual_default(p02, p1)) {
      if (!p02[2] && !p1[2]) {
        stream.lineStart();
        for (i2 = 0; i2 < n4; ++i2) stream.point((p02 = segment[i2])[0], p02[1]);
        stream.lineEnd();
        return;
      }
      p1[0] += 2 * epsilon;
    }
    subject.push(x3 = new Intersection(p02, segment, null, true));
    clip.push(x3.o = new Intersection(p02, null, x3, false));
    subject.push(x3 = new Intersection(p1, segment, null, false));
    clip.push(x3.o = new Intersection(p1, null, x3, true));
  });
  if (!subject.length) return;
  clip.sort(compareIntersection2);
  link(subject);
  link(clip);
  for (i2 = 0, n3 = clip.length; i2 < n3; ++i2) {
    clip[i2].e = startInside = !startInside;
  }
  var start = subject[0], points, point;
  while (1) {
    var current = start, isSubject = true;
    while (current.v) if ((current = current.n) === start) return;
    points = current.z;
    stream.lineStart();
    do {
      current.v = current.o.v = true;
      if (current.e) {
        if (isSubject) {
          for (i2 = 0, n3 = points.length; i2 < n3; ++i2) stream.point((point = points[i2])[0], point[1]);
        } else {
          interpolate(current.x, current.n.x, 1, stream);
        }
        current = current.n;
      } else {
        if (isSubject) {
          points = current.p.z;
          for (i2 = points.length - 1; i2 >= 0; --i2) stream.point((point = points[i2])[0], point[1]);
        } else {
          interpolate(current.x, current.p.x, -1, stream);
        }
        current = current.p;
      }
      current = current.o;
      points = current.z;
      isSubject = !isSubject;
    } while (!current.v);
    stream.lineEnd();
  }
}
function link(array) {
  if (!(n3 = array.length)) return;
  var n3, i2 = 0, a3 = array[0], b2;
  while (++i2 < n3) {
    a3.n = b2 = array[i2];
    b2.p = a3;
    a3 = b2;
  }
  a3.n = b2 = array[0];
  b2.p = a3;
}

// node_modules/d3-geo/src/polygonContains.js
function longitude(point) {
  return abs(point[0]) <= pi ? point[0] : sign(point[0]) * ((abs(point[0]) + pi) % tau - pi);
}
function polygonContains_default(polygon, point) {
  var lambda = longitude(point), phi = point[1], sinPhi = sin(phi), normal = [sin(lambda), -cos(lambda), 0], angle2 = 0, winding = 0;
  var sum = new Adder();
  if (sinPhi === 1) phi = halfPi + epsilon;
  else if (sinPhi === -1) phi = -halfPi - epsilon;
  for (var i2 = 0, n3 = polygon.length; i2 < n3; ++i2) {
    if (!(m = (ring = polygon[i2]).length)) continue;
    var ring, m, point0 = ring[m - 1], lambda04 = longitude(point0), phi02 = point0[1] / 2 + quarterPi, sinPhi03 = sin(phi02), cosPhi03 = cos(phi02);
    for (var j2 = 0; j2 < m; ++j2, lambda04 = lambda12, sinPhi03 = sinPhi1, cosPhi03 = cosPhi1, point0 = point1) {
      var point1 = ring[j2], lambda12 = longitude(point1), phi12 = point1[1] / 2 + quarterPi, sinPhi1 = sin(phi12), cosPhi1 = cos(phi12), delta = lambda12 - lambda04, sign2 = delta >= 0 ? 1 : -1, absDelta = sign2 * delta, antimeridian = absDelta > pi, k3 = sinPhi03 * sinPhi1;
      sum.add(atan2(k3 * sign2 * sin(absDelta), cosPhi03 * cosPhi1 + k3 * cos(absDelta)));
      angle2 += antimeridian ? delta + sign2 * tau : delta;
      if (antimeridian ^ lambda04 >= lambda ^ lambda12 >= lambda) {
        var arc = cartesianCross(cartesian(point0), cartesian(point1));
        cartesianNormalizeInPlace(arc);
        var intersection = cartesianCross(normal, arc);
        cartesianNormalizeInPlace(intersection);
        var phiArc = (antimeridian ^ delta >= 0 ? -1 : 1) * asin(intersection[2]);
        if (phi > phiArc || phi === phiArc && (arc[0] || arc[1])) {
          winding += antimeridian ^ delta >= 0 ? 1 : -1;
        }
      }
    }
  }
  return (angle2 < -epsilon || angle2 < epsilon && sum < -epsilon2) ^ winding & 1;
}

// node_modules/d3-geo/src/clip/index.js
function clip_default(pointVisible, clipLine, interpolate, start) {
  return function(sink) {
    var line = clipLine(sink), ringBuffer = buffer_default(), ringSink = clipLine(ringBuffer), polygonStarted = false, polygon, segments, ring;
    var clip = {
      point,
      lineStart,
      lineEnd,
      polygonStart: function() {
        clip.point = pointRing;
        clip.lineStart = ringStart;
        clip.lineEnd = ringEnd;
        segments = [];
        polygon = [];
      },
      polygonEnd: function() {
        clip.point = point;
        clip.lineStart = lineStart;
        clip.lineEnd = lineEnd;
        segments = merge(segments);
        var startInside = polygonContains_default(polygon, start);
        if (segments.length) {
          if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
          rejoin_default(segments, compareIntersection, startInside, interpolate, sink);
        } else if (startInside) {
          if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
          sink.lineStart();
          interpolate(null, null, 1, sink);
          sink.lineEnd();
        }
        if (polygonStarted) sink.polygonEnd(), polygonStarted = false;
        segments = polygon = null;
      },
      sphere: function() {
        sink.polygonStart();
        sink.lineStart();
        interpolate(null, null, 1, sink);
        sink.lineEnd();
        sink.polygonEnd();
      }
    };
    function point(lambda, phi) {
      if (pointVisible(lambda, phi)) sink.point(lambda, phi);
    }
    function pointLine(lambda, phi) {
      line.point(lambda, phi);
    }
    function lineStart() {
      clip.point = pointLine;
      line.lineStart();
    }
    function lineEnd() {
      clip.point = point;
      line.lineEnd();
    }
    function pointRing(lambda, phi) {
      ring.push([lambda, phi]);
      ringSink.point(lambda, phi);
    }
    function ringStart() {
      ringSink.lineStart();
      ring = [];
    }
    function ringEnd() {
      pointRing(ring[0][0], ring[0][1]);
      ringSink.lineEnd();
      var clean = ringSink.clean(), ringSegments = ringBuffer.result(), i2, n3 = ringSegments.length, m, segment, point2;
      ring.pop();
      polygon.push(ring);
      ring = null;
      if (!n3) return;
      if (clean & 1) {
        segment = ringSegments[0];
        if ((m = segment.length - 1) > 0) {
          if (!polygonStarted) sink.polygonStart(), polygonStarted = true;
          sink.lineStart();
          for (i2 = 0; i2 < m; ++i2) sink.point((point2 = segment[i2])[0], point2[1]);
          sink.lineEnd();
        }
        return;
      }
      if (n3 > 1 && clean & 2) ringSegments.push(ringSegments.pop().concat(ringSegments.shift()));
      segments.push(ringSegments.filter(validSegment));
    }
    return clip;
  };
}
function validSegment(segment) {
  return segment.length > 1;
}
function compareIntersection(a3, b2) {
  return ((a3 = a3.x)[0] < 0 ? a3[1] - halfPi - epsilon : halfPi - a3[1]) - ((b2 = b2.x)[0] < 0 ? b2[1] - halfPi - epsilon : halfPi - b2[1]);
}

// node_modules/d3-geo/src/clip/antimeridian.js
var antimeridian_default = clip_default(
  function() {
    return true;
  },
  clipAntimeridianLine,
  clipAntimeridianInterpolate,
  [-pi, -halfPi]
);
function clipAntimeridianLine(stream) {
  var lambda04 = NaN, phi02 = NaN, sign0 = NaN, clean;
  return {
    lineStart: function() {
      stream.lineStart();
      clean = 1;
    },
    point: function(lambda12, phi12) {
      var sign1 = lambda12 > 0 ? pi : -pi, delta = abs(lambda12 - lambda04);
      if (abs(delta - pi) < epsilon) {
        stream.point(lambda04, phi02 = (phi02 + phi12) / 2 > 0 ? halfPi : -halfPi);
        stream.point(sign0, phi02);
        stream.lineEnd();
        stream.lineStart();
        stream.point(sign1, phi02);
        stream.point(lambda12, phi02);
        clean = 0;
      } else if (sign0 !== sign1 && delta >= pi) {
        if (abs(lambda04 - sign0) < epsilon) lambda04 -= sign0 * epsilon;
        if (abs(lambda12 - sign1) < epsilon) lambda12 -= sign1 * epsilon;
        phi02 = clipAntimeridianIntersect(lambda04, phi02, lambda12, phi12);
        stream.point(sign0, phi02);
        stream.lineEnd();
        stream.lineStart();
        stream.point(sign1, phi02);
        clean = 0;
      }
      stream.point(lambda04 = lambda12, phi02 = phi12);
      sign0 = sign1;
    },
    lineEnd: function() {
      stream.lineEnd();
      lambda04 = phi02 = NaN;
    },
    clean: function() {
      return 2 - clean;
    }
  };
}
function clipAntimeridianIntersect(lambda04, phi02, lambda12, phi12) {
  var cosPhi03, cosPhi1, sinLambda0Lambda1 = sin(lambda04 - lambda12);
  return abs(sinLambda0Lambda1) > epsilon ? atan((sin(phi02) * (cosPhi1 = cos(phi12)) * sin(lambda12) - sin(phi12) * (cosPhi03 = cos(phi02)) * sin(lambda04)) / (cosPhi03 * cosPhi1 * sinLambda0Lambda1)) : (phi02 + phi12) / 2;
}
function clipAntimeridianInterpolate(from, to, direction, stream) {
  var phi;
  if (from == null) {
    phi = direction * halfPi;
    stream.point(-pi, phi);
    stream.point(0, phi);
    stream.point(pi, phi);
    stream.point(pi, 0);
    stream.point(pi, -phi);
    stream.point(0, -phi);
    stream.point(-pi, -phi);
    stream.point(-pi, 0);
    stream.point(-pi, phi);
  } else if (abs(from[0] - to[0]) > epsilon) {
    var lambda = from[0] < to[0] ? pi : -pi;
    phi = direction * lambda / 2;
    stream.point(-lambda, phi);
    stream.point(0, phi);
    stream.point(lambda, phi);
  } else {
    stream.point(to[0], to[1]);
  }
}

// node_modules/d3-geo/src/clip/circle.js
function circle_default2(radius) {
  var cr = cos(radius), delta = 2 * radians, smallRadius = cr > 0, notHemisphere = abs(cr) > epsilon;
  function interpolate(from, to, direction, stream) {
    circleStream(stream, radius, delta, direction, from, to);
  }
  function visible(lambda, phi) {
    return cos(lambda) * cos(phi) > cr;
  }
  function clipLine(stream) {
    var point0, c0, v0, v00, clean;
    return {
      lineStart: function() {
        v00 = v0 = false;
        clean = 1;
      },
      point: function(lambda, phi) {
        var point1 = [lambda, phi], point2, v3 = visible(lambda, phi), c3 = smallRadius ? v3 ? 0 : code(lambda, phi) : v3 ? code(lambda + (lambda < 0 ? pi : -pi), phi) : 0;
        if (!point0 && (v00 = v0 = v3)) stream.lineStart();
        if (v3 !== v0) {
          point2 = intersect(point0, point1);
          if (!point2 || pointEqual_default(point0, point2) || pointEqual_default(point1, point2))
            point1[2] = 1;
        }
        if (v3 !== v0) {
          clean = 0;
          if (v3) {
            stream.lineStart();
            point2 = intersect(point1, point0);
            stream.point(point2[0], point2[1]);
          } else {
            point2 = intersect(point0, point1);
            stream.point(point2[0], point2[1], 2);
            stream.lineEnd();
          }
          point0 = point2;
        } else if (notHemisphere && point0 && smallRadius ^ v3) {
          var t3;
          if (!(c3 & c0) && (t3 = intersect(point1, point0, true))) {
            clean = 0;
            if (smallRadius) {
              stream.lineStart();
              stream.point(t3[0][0], t3[0][1]);
              stream.point(t3[1][0], t3[1][1]);
              stream.lineEnd();
            } else {
              stream.point(t3[1][0], t3[1][1]);
              stream.lineEnd();
              stream.lineStart();
              stream.point(t3[0][0], t3[0][1], 3);
            }
          }
        }
        if (v3 && (!point0 || !pointEqual_default(point0, point1))) {
          stream.point(point1[0], point1[1]);
        }
        point0 = point1, v0 = v3, c0 = c3;
      },
      lineEnd: function() {
        if (v0) stream.lineEnd();
        point0 = null;
      },
      // Rejoin first and last segments if there were intersections and the first
      // and last points were visible.
      clean: function() {
        return clean | (v00 && v0) << 1;
      }
    };
  }
  function intersect(a3, b2, two) {
    var pa = cartesian(a3), pb = cartesian(b2);
    var n1 = [1, 0, 0], n22 = cartesianCross(pa, pb), n2n2 = cartesianDot(n22, n22), n1n2 = n22[0], determinant = n2n2 - n1n2 * n1n2;
    if (!determinant) return !two && a3;
    var c1 = cr * n2n2 / determinant, c22 = -cr * n1n2 / determinant, n1xn2 = cartesianCross(n1, n22), A5 = cartesianScale(n1, c1), B = cartesianScale(n22, c22);
    cartesianAddInPlace(A5, B);
    var u = n1xn2, w2 = cartesianDot(A5, u), uu = cartesianDot(u, u), t22 = w2 * w2 - uu * (cartesianDot(A5, A5) - 1);
    if (t22 < 0) return;
    var t3 = sqrt(t22), q2 = cartesianScale(u, (-w2 - t3) / uu);
    cartesianAddInPlace(q2, A5);
    q2 = spherical(q2);
    if (!two) return q2;
    var lambda04 = a3[0], lambda12 = b2[0], phi02 = a3[1], phi12 = b2[1], z;
    if (lambda12 < lambda04) z = lambda04, lambda04 = lambda12, lambda12 = z;
    var delta2 = lambda12 - lambda04, polar = abs(delta2 - pi) < epsilon, meridian = polar || delta2 < epsilon;
    if (!polar && phi12 < phi02) z = phi02, phi02 = phi12, phi12 = z;
    if (meridian ? polar ? phi02 + phi12 > 0 ^ q2[1] < (abs(q2[0] - lambda04) < epsilon ? phi02 : phi12) : phi02 <= q2[1] && q2[1] <= phi12 : delta2 > pi ^ (lambda04 <= q2[0] && q2[0] <= lambda12)) {
      var q1 = cartesianScale(u, (-w2 + t3) / uu);
      cartesianAddInPlace(q1, A5);
      return [q2, spherical(q1)];
    }
  }
  function code(lambda, phi) {
    var r3 = smallRadius ? radius : pi - radius, code2 = 0;
    if (lambda < -r3) code2 |= 1;
    else if (lambda > r3) code2 |= 2;
    if (phi < -r3) code2 |= 4;
    else if (phi > r3) code2 |= 8;
    return code2;
  }
  return clip_default(visible, clipLine, interpolate, smallRadius ? [0, -radius] : [-pi, radius - pi]);
}

// node_modules/d3-geo/src/clip/line.js
function line_default(a3, b2, x06, y06, x12, y12) {
  var ax = a3[0], ay = a3[1], bx = b2[0], by = b2[1], t0 = 0, t1 = 1, dx = bx - ax, dy = by - ay, r3;
  r3 = x06 - ax;
  if (!dx && r3 > 0) return;
  r3 /= dx;
  if (dx < 0) {
    if (r3 < t0) return;
    if (r3 < t1) t1 = r3;
  } else if (dx > 0) {
    if (r3 > t1) return;
    if (r3 > t0) t0 = r3;
  }
  r3 = x12 - ax;
  if (!dx && r3 < 0) return;
  r3 /= dx;
  if (dx < 0) {
    if (r3 > t1) return;
    if (r3 > t0) t0 = r3;
  } else if (dx > 0) {
    if (r3 < t0) return;
    if (r3 < t1) t1 = r3;
  }
  r3 = y06 - ay;
  if (!dy && r3 > 0) return;
  r3 /= dy;
  if (dy < 0) {
    if (r3 < t0) return;
    if (r3 < t1) t1 = r3;
  } else if (dy > 0) {
    if (r3 > t1) return;
    if (r3 > t0) t0 = r3;
  }
  r3 = y12 - ay;
  if (!dy && r3 < 0) return;
  r3 /= dy;
  if (dy < 0) {
    if (r3 > t1) return;
    if (r3 > t0) t0 = r3;
  } else if (dy > 0) {
    if (r3 < t0) return;
    if (r3 < t1) t1 = r3;
  }
  if (t0 > 0) a3[0] = ax + t0 * dx, a3[1] = ay + t0 * dy;
  if (t1 < 1) b2[0] = ax + t1 * dx, b2[1] = ay + t1 * dy;
  return true;
}

// node_modules/d3-geo/src/clip/rectangle.js
var clipMax = 1e9;
var clipMin = -clipMax;
function clipRectangle(x06, y06, x12, y12) {
  function visible(x3, y3) {
    return x06 <= x3 && x3 <= x12 && y06 <= y3 && y3 <= y12;
  }
  function interpolate(from, to, direction, stream) {
    var a3 = 0, a1 = 0;
    if (from == null || (a3 = corner(from, direction)) !== (a1 = corner(to, direction)) || comparePoint(from, to) < 0 ^ direction > 0) {
      do
        stream.point(a3 === 0 || a3 === 3 ? x06 : x12, a3 > 1 ? y12 : y06);
      while ((a3 = (a3 + direction + 4) % 4) !== a1);
    } else {
      stream.point(to[0], to[1]);
    }
  }
  function corner(p, direction) {
    return abs(p[0] - x06) < epsilon ? direction > 0 ? 0 : 3 : abs(p[0] - x12) < epsilon ? direction > 0 ? 2 : 1 : abs(p[1] - y06) < epsilon ? direction > 0 ? 1 : 0 : direction > 0 ? 3 : 2;
  }
  function compareIntersection2(a3, b2) {
    return comparePoint(a3.x, b2.x);
  }
  function comparePoint(a3, b2) {
    var ca = corner(a3, 1), cb = corner(b2, 1);
    return ca !== cb ? ca - cb : ca === 0 ? b2[1] - a3[1] : ca === 1 ? a3[0] - b2[0] : ca === 2 ? a3[1] - b2[1] : b2[0] - a3[0];
  }
  return function(stream) {
    var activeStream = stream, bufferStream = buffer_default(), segments, polygon, ring, x__, y__, v__, x_, y_, v_, first, clean;
    var clipStream = {
      point,
      lineStart,
      lineEnd,
      polygonStart,
      polygonEnd
    };
    function point(x3, y3) {
      if (visible(x3, y3)) activeStream.point(x3, y3);
    }
    function polygonInside() {
      var winding = 0;
      for (var i2 = 0, n3 = polygon.length; i2 < n3; ++i2) {
        for (var ring2 = polygon[i2], j2 = 1, m = ring2.length, point2 = ring2[0], a0, a1, b0 = point2[0], b1 = point2[1]; j2 < m; ++j2) {
          a0 = b0, a1 = b1, point2 = ring2[j2], b0 = point2[0], b1 = point2[1];
          if (a1 <= y12) {
            if (b1 > y12 && (b0 - a0) * (y12 - a1) > (b1 - a1) * (x06 - a0)) ++winding;
          } else {
            if (b1 <= y12 && (b0 - a0) * (y12 - a1) < (b1 - a1) * (x06 - a0)) --winding;
          }
        }
      }
      return winding;
    }
    function polygonStart() {
      activeStream = bufferStream, segments = [], polygon = [], clean = true;
    }
    function polygonEnd() {
      var startInside = polygonInside(), cleanInside = clean && startInside, visible2 = (segments = merge(segments)).length;
      if (cleanInside || visible2) {
        stream.polygonStart();
        if (cleanInside) {
          stream.lineStart();
          interpolate(null, null, 1, stream);
          stream.lineEnd();
        }
        if (visible2) {
          rejoin_default(segments, compareIntersection2, startInside, interpolate, stream);
        }
        stream.polygonEnd();
      }
      activeStream = stream, segments = polygon = ring = null;
    }
    function lineStart() {
      clipStream.point = linePoint2;
      if (polygon) polygon.push(ring = []);
      first = true;
      v_ = false;
      x_ = y_ = NaN;
    }
    function lineEnd() {
      if (segments) {
        linePoint2(x__, y__);
        if (v__ && v_) bufferStream.rejoin();
        segments.push(bufferStream.result());
      }
      clipStream.point = point;
      if (v_) activeStream.lineEnd();
    }
    function linePoint2(x3, y3) {
      var v3 = visible(x3, y3);
      if (polygon) ring.push([x3, y3]);
      if (first) {
        x__ = x3, y__ = y3, v__ = v3;
        first = false;
        if (v3) {
          activeStream.lineStart();
          activeStream.point(x3, y3);
        }
      } else {
        if (v3 && v_) activeStream.point(x3, y3);
        else {
          var a3 = [x_ = Math.max(clipMin, Math.min(clipMax, x_)), y_ = Math.max(clipMin, Math.min(clipMax, y_))], b2 = [x3 = Math.max(clipMin, Math.min(clipMax, x3)), y3 = Math.max(clipMin, Math.min(clipMax, y3))];
          if (line_default(a3, b2, x06, y06, x12, y12)) {
            if (!v_) {
              activeStream.lineStart();
              activeStream.point(a3[0], a3[1]);
            }
            activeStream.point(b2[0], b2[1]);
            if (!v3) activeStream.lineEnd();
            clean = false;
          } else if (v3) {
            activeStream.lineStart();
            activeStream.point(x3, y3);
            clean = false;
          }
        }
      }
      x_ = x3, y_ = y3, v_ = v3;
    }
    return clipStream;
  };
}

// node_modules/d3-geo/src/clip/extent.js
function extent_default() {
  var x06 = 0, y06 = 0, x12 = 960, y12 = 500, cache, cacheStream, clip;
  return clip = {
    stream: function(stream) {
      return cache && cacheStream === stream ? cache : cache = clipRectangle(x06, y06, x12, y12)(cacheStream = stream);
    },
    extent: function(_) {
      return arguments.length ? (x06 = +_[0][0], y06 = +_[0][1], x12 = +_[1][0], y12 = +_[1][1], cache = cacheStream = null, clip) : [[x06, y06], [x12, y12]];
    }
  };
}

// node_modules/d3-geo/src/length.js
var lengthSum;
var lambda03;
var sinPhi02;
var cosPhi02;
var lengthStream = {
  sphere: noop,
  point: noop,
  lineStart: lengthLineStart,
  lineEnd: noop,
  polygonStart: noop,
  polygonEnd: noop
};
function lengthLineStart() {
  lengthStream.point = lengthPointFirst;
  lengthStream.lineEnd = lengthLineEnd;
}
function lengthLineEnd() {
  lengthStream.point = lengthStream.lineEnd = noop;
}
function lengthPointFirst(lambda, phi) {
  lambda *= radians, phi *= radians;
  lambda03 = lambda, sinPhi02 = sin(phi), cosPhi02 = cos(phi);
  lengthStream.point = lengthPoint;
}
function lengthPoint(lambda, phi) {
  lambda *= radians, phi *= radians;
  var sinPhi = sin(phi), cosPhi = cos(phi), delta = abs(lambda - lambda03), cosDelta = cos(delta), sinDelta = sin(delta), x3 = cosPhi * sinDelta, y3 = cosPhi02 * sinPhi - sinPhi02 * cosPhi * cosDelta, z = sinPhi02 * sinPhi + cosPhi02 * cosPhi * cosDelta;
  lengthSum.add(atan2(sqrt(x3 * x3 + y3 * y3), z));
  lambda03 = lambda, sinPhi02 = sinPhi, cosPhi02 = cosPhi;
}
function length_default(object3) {
  lengthSum = new Adder();
  stream_default(object3, lengthStream);
  return +lengthSum;
}

// node_modules/d3-geo/src/distance.js
var coordinates = [null, null];
var object = { type: "LineString", coordinates };
function distance_default(a3, b2) {
  coordinates[0] = a3;
  coordinates[1] = b2;
  return length_default(object);
}

// node_modules/d3-geo/src/contains.js
var containsObjectType = {
  Feature: function(object3, point) {
    return containsGeometry(object3.geometry, point);
  },
  FeatureCollection: function(object3, point) {
    var features = object3.features, i2 = -1, n3 = features.length;
    while (++i2 < n3) if (containsGeometry(features[i2].geometry, point)) return true;
    return false;
  }
};
var containsGeometryType = {
  Sphere: function() {
    return true;
  },
  Point: function(object3, point) {
    return containsPoint(object3.coordinates, point);
  },
  MultiPoint: function(object3, point) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) if (containsPoint(coordinates2[i2], point)) return true;
    return false;
  },
  LineString: function(object3, point) {
    return containsLine(object3.coordinates, point);
  },
  MultiLineString: function(object3, point) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) if (containsLine(coordinates2[i2], point)) return true;
    return false;
  },
  Polygon: function(object3, point) {
    return containsPolygon(object3.coordinates, point);
  },
  MultiPolygon: function(object3, point) {
    var coordinates2 = object3.coordinates, i2 = -1, n3 = coordinates2.length;
    while (++i2 < n3) if (containsPolygon(coordinates2[i2], point)) return true;
    return false;
  },
  GeometryCollection: function(object3, point) {
    var geometries = object3.geometries, i2 = -1, n3 = geometries.length;
    while (++i2 < n3) if (containsGeometry(geometries[i2], point)) return true;
    return false;
  }
};
function containsGeometry(geometry, point) {
  return geometry && containsGeometryType.hasOwnProperty(geometry.type) ? containsGeometryType[geometry.type](geometry, point) : false;
}
function containsPoint(coordinates2, point) {
  return distance_default(coordinates2, point) === 0;
}
function containsLine(coordinates2, point) {
  var ao, bo, ab;
  for (var i2 = 0, n3 = coordinates2.length; i2 < n3; i2++) {
    bo = distance_default(coordinates2[i2], point);
    if (bo === 0) return true;
    if (i2 > 0) {
      ab = distance_default(coordinates2[i2], coordinates2[i2 - 1]);
      if (ab > 0 && ao <= ab && bo <= ab && (ao + bo - ab) * (1 - Math.pow((ao - bo) / ab, 2)) < epsilon2 * ab)
        return true;
    }
    ao = bo;
  }
  return false;
}
function containsPolygon(coordinates2, point) {
  return !!polygonContains_default(coordinates2.map(ringRadians), pointRadians(point));
}
function ringRadians(ring) {
  return ring = ring.map(pointRadians), ring.pop(), ring;
}
function pointRadians(point) {
  return [point[0] * radians, point[1] * radians];
}
function contains_default(object3, point) {
  return (object3 && containsObjectType.hasOwnProperty(object3.type) ? containsObjectType[object3.type] : containsGeometry)(object3, point);
}

// node_modules/d3-geo/src/graticule.js
function graticuleX(y06, y12, dy) {
  var y3 = range(y06, y12 - epsilon, dy).concat(y12);
  return function(x3) {
    return y3.map(function(y4) {
      return [x3, y4];
    });
  };
}
function graticuleY(x06, x12, dx) {
  var x3 = range(x06, x12 - epsilon, dx).concat(x12);
  return function(y3) {
    return x3.map(function(x4) {
      return [x4, y3];
    });
  };
}
function graticule() {
  var x12, x06, X13, X03, y12, y06, Y13, Y03, dx = 10, dy = dx, DX = 90, DY = 360, x3, y3, X, Y, precision = 2.5;
  function graticule2() {
    return { type: "MultiLineString", coordinates: lines() };
  }
  function lines() {
    return range(ceil(X03 / DX) * DX, X13, DX).map(X).concat(range(ceil(Y03 / DY) * DY, Y13, DY).map(Y)).concat(range(ceil(x06 / dx) * dx, x12, dx).filter(function(x4) {
      return abs(x4 % DX) > epsilon;
    }).map(x3)).concat(range(ceil(y06 / dy) * dy, y12, dy).filter(function(y4) {
      return abs(y4 % DY) > epsilon;
    }).map(y3));
  }
  graticule2.lines = function() {
    return lines().map(function(coordinates2) {
      return { type: "LineString", coordinates: coordinates2 };
    });
  };
  graticule2.outline = function() {
    return {
      type: "Polygon",
      coordinates: [
        X(X03).concat(
          Y(Y13).slice(1),
          X(X13).reverse().slice(1),
          Y(Y03).reverse().slice(1)
        )
      ]
    };
  };
  graticule2.extent = function(_) {
    if (!arguments.length) return graticule2.extentMinor();
    return graticule2.extentMajor(_).extentMinor(_);
  };
  graticule2.extentMajor = function(_) {
    if (!arguments.length) return [[X03, Y03], [X13, Y13]];
    X03 = +_[0][0], X13 = +_[1][0];
    Y03 = +_[0][1], Y13 = +_[1][1];
    if (X03 > X13) _ = X03, X03 = X13, X13 = _;
    if (Y03 > Y13) _ = Y03, Y03 = Y13, Y13 = _;
    return graticule2.precision(precision);
  };
  graticule2.extentMinor = function(_) {
    if (!arguments.length) return [[x06, y06], [x12, y12]];
    x06 = +_[0][0], x12 = +_[1][0];
    y06 = +_[0][1], y12 = +_[1][1];
    if (x06 > x12) _ = x06, x06 = x12, x12 = _;
    if (y06 > y12) _ = y06, y06 = y12, y12 = _;
    return graticule2.precision(precision);
  };
  graticule2.step = function(_) {
    if (!arguments.length) return graticule2.stepMinor();
    return graticule2.stepMajor(_).stepMinor(_);
  };
  graticule2.stepMajor = function(_) {
    if (!arguments.length) return [DX, DY];
    DX = +_[0], DY = +_[1];
    return graticule2;
  };
  graticule2.stepMinor = function(_) {
    if (!arguments.length) return [dx, dy];
    dx = +_[0], dy = +_[1];
    return graticule2;
  };
  graticule2.precision = function(_) {
    if (!arguments.length) return precision;
    precision = +_;
    x3 = graticuleX(y06, y12, 90);
    y3 = graticuleY(x06, x12, precision);
    X = graticuleX(Y03, Y13, 90);
    Y = graticuleY(X03, X13, precision);
    return graticule2;
  };
  return graticule2.extentMajor([[-180, -90 + epsilon], [180, 90 - epsilon]]).extentMinor([[-180, -80 - epsilon], [180, 80 + epsilon]]);
}
function graticule10() {
  return graticule()();
}

// node_modules/d3-geo/src/interpolate.js
function interpolate_default(a3, b2) {
  var x06 = a3[0] * radians, y06 = a3[1] * radians, x12 = b2[0] * radians, y12 = b2[1] * radians, cy0 = cos(y06), sy0 = sin(y06), cy1 = cos(y12), sy1 = sin(y12), kx0 = cy0 * cos(x06), ky0 = cy0 * sin(x06), kx1 = cy1 * cos(x12), ky1 = cy1 * sin(x12), d3 = 2 * asin(sqrt(haversin(y12 - y06) + cy0 * cy1 * haversin(x12 - x06))), k3 = sin(d3);
  var interpolate = d3 ? function(t3) {
    var B = sin(t3 *= d3) / k3, A5 = sin(d3 - t3) / k3, x3 = A5 * kx0 + B * kx1, y3 = A5 * ky0 + B * ky1, z = A5 * sy0 + B * sy1;
    return [
      atan2(y3, x3) * degrees,
      atan2(z, sqrt(x3 * x3 + y3 * y3)) * degrees
    ];
  } : function() {
    return [x06 * degrees, y06 * degrees];
  };
  interpolate.distance = d3;
  return interpolate;
}

// node_modules/d3-geo/src/identity.js
var identity_default = (x3) => x3;

// node_modules/d3-geo/src/path/area.js
var areaSum2 = new Adder();
var areaRingSum2 = new Adder();
var x00;
var y00;
var x02;
var y02;
var areaStream2 = {
  point: noop,
  lineStart: noop,
  lineEnd: noop,
  polygonStart: function() {
    areaStream2.lineStart = areaRingStart2;
    areaStream2.lineEnd = areaRingEnd2;
  },
  polygonEnd: function() {
    areaStream2.lineStart = areaStream2.lineEnd = areaStream2.point = noop;
    areaSum2.add(abs(areaRingSum2));
    areaRingSum2 = new Adder();
  },
  result: function() {
    var area = areaSum2 / 2;
    areaSum2 = new Adder();
    return area;
  }
};
function areaRingStart2() {
  areaStream2.point = areaPointFirst2;
}
function areaPointFirst2(x3, y3) {
  areaStream2.point = areaPoint2;
  x00 = x02 = x3, y00 = y02 = y3;
}
function areaPoint2(x3, y3) {
  areaRingSum2.add(y02 * x3 - x02 * y3);
  x02 = x3, y02 = y3;
}
function areaRingEnd2() {
  areaPoint2(x00, y00);
}
var area_default2 = areaStream2;

// node_modules/d3-geo/src/path/bounds.js
var x03 = Infinity;
var y03 = x03;
var x1 = -x03;
var y1 = x1;
var boundsStream2 = {
  point: boundsPoint2,
  lineStart: noop,
  lineEnd: noop,
  polygonStart: noop,
  polygonEnd: noop,
  result: function() {
    var bounds = [[x03, y03], [x1, y1]];
    x1 = y1 = -(y03 = x03 = Infinity);
    return bounds;
  }
};
function boundsPoint2(x3, y3) {
  if (x3 < x03) x03 = x3;
  if (x3 > x1) x1 = x3;
  if (y3 < y03) y03 = y3;
  if (y3 > y1) y1 = y3;
}
var bounds_default2 = boundsStream2;

// node_modules/d3-geo/src/path/centroid.js
var X02 = 0;
var Y02 = 0;
var Z02 = 0;
var X12 = 0;
var Y12 = 0;
var Z12 = 0;
var X22 = 0;
var Y22 = 0;
var Z22 = 0;
var x002;
var y002;
var x04;
var y04;
var centroidStream2 = {
  point: centroidPoint2,
  lineStart: centroidLineStart2,
  lineEnd: centroidLineEnd2,
  polygonStart: function() {
    centroidStream2.lineStart = centroidRingStart2;
    centroidStream2.lineEnd = centroidRingEnd2;
  },
  polygonEnd: function() {
    centroidStream2.point = centroidPoint2;
    centroidStream2.lineStart = centroidLineStart2;
    centroidStream2.lineEnd = centroidLineEnd2;
  },
  result: function() {
    var centroid = Z22 ? [X22 / Z22, Y22 / Z22] : Z12 ? [X12 / Z12, Y12 / Z12] : Z02 ? [X02 / Z02, Y02 / Z02] : [NaN, NaN];
    X02 = Y02 = Z02 = X12 = Y12 = Z12 = X22 = Y22 = Z22 = 0;
    return centroid;
  }
};
function centroidPoint2(x3, y3) {
  X02 += x3;
  Y02 += y3;
  ++Z02;
}
function centroidLineStart2() {
  centroidStream2.point = centroidPointFirstLine;
}
function centroidPointFirstLine(x3, y3) {
  centroidStream2.point = centroidPointLine;
  centroidPoint2(x04 = x3, y04 = y3);
}
function centroidPointLine(x3, y3) {
  var dx = x3 - x04, dy = y3 - y04, z = sqrt(dx * dx + dy * dy);
  X12 += z * (x04 + x3) / 2;
  Y12 += z * (y04 + y3) / 2;
  Z12 += z;
  centroidPoint2(x04 = x3, y04 = y3);
}
function centroidLineEnd2() {
  centroidStream2.point = centroidPoint2;
}
function centroidRingStart2() {
  centroidStream2.point = centroidPointFirstRing;
}
function centroidRingEnd2() {
  centroidPointRing(x002, y002);
}
function centroidPointFirstRing(x3, y3) {
  centroidStream2.point = centroidPointRing;
  centroidPoint2(x002 = x04 = x3, y002 = y04 = y3);
}
function centroidPointRing(x3, y3) {
  var dx = x3 - x04, dy = y3 - y04, z = sqrt(dx * dx + dy * dy);
  X12 += z * (x04 + x3) / 2;
  Y12 += z * (y04 + y3) / 2;
  Z12 += z;
  z = y04 * x3 - x04 * y3;
  X22 += z * (x04 + x3);
  Y22 += z * (y04 + y3);
  Z22 += z * 3;
  centroidPoint2(x04 = x3, y04 = y3);
}
var centroid_default2 = centroidStream2;

// node_modules/d3-geo/src/path/context.js
function PathContext(context) {
  this._context = context;
}
PathContext.prototype = {
  _radius: 4.5,
  pointRadius: function(_) {
    return this._radius = _, this;
  },
  polygonStart: function() {
    this._line = 0;
  },
  polygonEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._point = 0;
  },
  lineEnd: function() {
    if (this._line === 0) this._context.closePath();
    this._point = NaN;
  },
  point: function(x3, y3) {
    switch (this._point) {
      case 0: {
        this._context.moveTo(x3, y3);
        this._point = 1;
        break;
      }
      case 1: {
        this._context.lineTo(x3, y3);
        break;
      }
      default: {
        this._context.moveTo(x3 + this._radius, y3);
        this._context.arc(x3, y3, this._radius, 0, tau);
        break;
      }
    }
  },
  result: noop
};

// node_modules/d3-geo/src/path/measure.js
var lengthSum2 = new Adder();
var lengthRing;
var x003;
var y003;
var x05;
var y05;
var lengthStream2 = {
  point: noop,
  lineStart: function() {
    lengthStream2.point = lengthPointFirst2;
  },
  lineEnd: function() {
    if (lengthRing) lengthPoint2(x003, y003);
    lengthStream2.point = noop;
  },
  polygonStart: function() {
    lengthRing = true;
  },
  polygonEnd: function() {
    lengthRing = null;
  },
  result: function() {
    var length = +lengthSum2;
    lengthSum2 = new Adder();
    return length;
  }
};
function lengthPointFirst2(x3, y3) {
  lengthStream2.point = lengthPoint2;
  x003 = x05 = x3, y003 = y05 = y3;
}
function lengthPoint2(x3, y3) {
  x05 -= x3, y05 -= y3;
  lengthSum2.add(sqrt(x05 * x05 + y05 * y05));
  x05 = x3, y05 = y3;
}
var measure_default = lengthStream2;

// node_modules/d3-geo/src/path/string.js
var cacheDigits;
var cacheAppend;
var cacheRadius;
var cacheCircle;
var PathString = class {
  constructor(digits) {
    this._append = digits == null ? append : appendRound(digits);
    this._radius = 4.5;
    this._ = "";
  }
  pointRadius(_) {
    this._radius = +_;
    return this;
  }
  polygonStart() {
    this._line = 0;
  }
  polygonEnd() {
    this._line = NaN;
  }
  lineStart() {
    this._point = 0;
  }
  lineEnd() {
    if (this._line === 0) this._ += "Z";
    this._point = NaN;
  }
  point(x3, y3) {
    switch (this._point) {
      case 0: {
        this._append`M${x3},${y3}`;
        this._point = 1;
        break;
      }
      case 1: {
        this._append`L${x3},${y3}`;
        break;
      }
      default: {
        this._append`M${x3},${y3}`;
        if (this._radius !== cacheRadius || this._append !== cacheAppend) {
          const r3 = this._radius;
          const s2 = this._;
          this._ = "";
          this._append`m0,${r3}a${r3},${r3} 0 1,1 0,${-2 * r3}a${r3},${r3} 0 1,1 0,${2 * r3}z`;
          cacheRadius = r3;
          cacheAppend = this._append;
          cacheCircle = this._;
          this._ = s2;
        }
        this._ += cacheCircle;
        break;
      }
    }
  }
  result() {
    const result = this._;
    this._ = "";
    return result.length ? result : null;
  }
};
function append(strings) {
  let i2 = 1;
  this._ += strings[0];
  for (const j2 = strings.length; i2 < j2; ++i2) {
    this._ += arguments[i2] + strings[i2];
  }
}
function appendRound(digits) {
  const d3 = Math.floor(digits);
  if (!(d3 >= 0)) throw new RangeError(`invalid digits: ${digits}`);
  if (d3 > 15) return append;
  if (d3 !== cacheDigits) {
    const k3 = 10 ** d3;
    cacheDigits = d3;
    cacheAppend = function append2(strings) {
      let i2 = 1;
      this._ += strings[0];
      for (const j2 = strings.length; i2 < j2; ++i2) {
        this._ += Math.round(arguments[i2] * k3) / k3 + strings[i2];
      }
    };
  }
  return cacheAppend;
}

// node_modules/d3-geo/src/path/index.js
function path_default(projection2, context) {
  let digits = 3, pointRadius = 4.5, projectionStream, contextStream;
  function path(object3) {
    if (object3) {
      if (typeof pointRadius === "function") contextStream.pointRadius(+pointRadius.apply(this, arguments));
      stream_default(object3, projectionStream(contextStream));
    }
    return contextStream.result();
  }
  path.area = function(object3) {
    stream_default(object3, projectionStream(area_default2));
    return area_default2.result();
  };
  path.measure = function(object3) {
    stream_default(object3, projectionStream(measure_default));
    return measure_default.result();
  };
  path.bounds = function(object3) {
    stream_default(object3, projectionStream(bounds_default2));
    return bounds_default2.result();
  };
  path.centroid = function(object3) {
    stream_default(object3, projectionStream(centroid_default2));
    return centroid_default2.result();
  };
  path.projection = function(_) {
    if (!arguments.length) return projection2;
    projectionStream = _ == null ? (projection2 = null, identity_default) : (projection2 = _).stream;
    return path;
  };
  path.context = function(_) {
    if (!arguments.length) return context;
    contextStream = _ == null ? (context = null, new PathString(digits)) : new PathContext(context = _);
    if (typeof pointRadius !== "function") contextStream.pointRadius(pointRadius);
    return path;
  };
  path.pointRadius = function(_) {
    if (!arguments.length) return pointRadius;
    pointRadius = typeof _ === "function" ? _ : (contextStream.pointRadius(+_), +_);
    return path;
  };
  path.digits = function(_) {
    if (!arguments.length) return digits;
    if (_ == null) digits = null;
    else {
      const d3 = Math.floor(_);
      if (!(d3 >= 0)) throw new RangeError(`invalid digits: ${_}`);
      digits = d3;
    }
    if (context === null) contextStream = new PathString(digits);
    return path;
  };
  return path.projection(projection2).digits(digits).context(context);
}

// node_modules/d3-geo/src/transform.js
function transform_default(methods) {
  return {
    stream: transformer(methods)
  };
}
function transformer(methods) {
  return function(stream) {
    var s2 = new TransformStream();
    for (var key in methods) s2[key] = methods[key];
    s2.stream = stream;
    return s2;
  };
}
function TransformStream() {
}
TransformStream.prototype = {
  constructor: TransformStream,
  point: function(x3, y3) {
    this.stream.point(x3, y3);
  },
  sphere: function() {
    this.stream.sphere();
  },
  lineStart: function() {
    this.stream.lineStart();
  },
  lineEnd: function() {
    this.stream.lineEnd();
  },
  polygonStart: function() {
    this.stream.polygonStart();
  },
  polygonEnd: function() {
    this.stream.polygonEnd();
  }
};

// node_modules/d3-geo/src/projection/fit.js
function fit(projection2, fitBounds, object3) {
  var clip = projection2.clipExtent && projection2.clipExtent();
  projection2.scale(150).translate([0, 0]);
  if (clip != null) projection2.clipExtent(null);
  stream_default(object3, projection2.stream(bounds_default2));
  fitBounds(bounds_default2.result());
  if (clip != null) projection2.clipExtent(clip);
  return projection2;
}
function fitExtent(projection2, extent, object3) {
  return fit(projection2, function(b2) {
    var w2 = extent[1][0] - extent[0][0], h = extent[1][1] - extent[0][1], k3 = Math.min(w2 / (b2[1][0] - b2[0][0]), h / (b2[1][1] - b2[0][1])), x3 = +extent[0][0] + (w2 - k3 * (b2[1][0] + b2[0][0])) / 2, y3 = +extent[0][1] + (h - k3 * (b2[1][1] + b2[0][1])) / 2;
    projection2.scale(150 * k3).translate([x3, y3]);
  }, object3);
}
function fitSize(projection2, size, object3) {
  return fitExtent(projection2, [[0, 0], size], object3);
}
function fitWidth(projection2, width, object3) {
  return fit(projection2, function(b2) {
    var w2 = +width, k3 = w2 / (b2[1][0] - b2[0][0]), x3 = (w2 - k3 * (b2[1][0] + b2[0][0])) / 2, y3 = -k3 * b2[0][1];
    projection2.scale(150 * k3).translate([x3, y3]);
  }, object3);
}
function fitHeight(projection2, height, object3) {
  return fit(projection2, function(b2) {
    var h = +height, k3 = h / (b2[1][1] - b2[0][1]), x3 = -k3 * b2[0][0], y3 = (h - k3 * (b2[1][1] + b2[0][1])) / 2;
    projection2.scale(150 * k3).translate([x3, y3]);
  }, object3);
}

// node_modules/d3-geo/src/projection/resample.js
var maxDepth = 16;
var cosMinDistance = cos(30 * radians);
function resample_default(project, delta2) {
  return +delta2 ? resample(project, delta2) : resampleNone(project);
}
function resampleNone(project) {
  return transformer({
    point: function(x3, y3) {
      x3 = project(x3, y3);
      this.stream.point(x3[0], x3[1]);
    }
  });
}
function resample(project, delta2) {
  function resampleLineTo(x06, y06, lambda04, a0, b0, c0, x12, y12, lambda12, a1, b1, c1, depth, stream) {
    var dx = x12 - x06, dy = y12 - y06, d22 = dx * dx + dy * dy;
    if (d22 > 4 * delta2 && depth--) {
      var a3 = a0 + a1, b2 = b0 + b1, c3 = c0 + c1, m = sqrt(a3 * a3 + b2 * b2 + c3 * c3), phi2 = asin(c3 /= m), lambda22 = abs(abs(c3) - 1) < epsilon || abs(lambda04 - lambda12) < epsilon ? (lambda04 + lambda12) / 2 : atan2(b2, a3), p = project(lambda22, phi2), x22 = p[0], y22 = p[1], dx2 = x22 - x06, dy2 = y22 - y06, dz = dy * dx2 - dx * dy2;
      if (dz * dz / d22 > delta2 || abs((dx * dx2 + dy * dy2) / d22 - 0.5) > 0.3 || a0 * a1 + b0 * b1 + c0 * c1 < cosMinDistance) {
        resampleLineTo(x06, y06, lambda04, a0, b0, c0, x22, y22, lambda22, a3 /= m, b2 /= m, c3, depth, stream);
        stream.point(x22, y22);
        resampleLineTo(x22, y22, lambda22, a3, b2, c3, x12, y12, lambda12, a1, b1, c1, depth, stream);
      }
    }
  }
  return function(stream) {
    var lambda004, x004, y004, a00, b00, c00, lambda04, x06, y06, a0, b0, c0;
    var resampleStream = {
      point,
      lineStart,
      lineEnd,
      polygonStart: function() {
        stream.polygonStart();
        resampleStream.lineStart = ringStart;
      },
      polygonEnd: function() {
        stream.polygonEnd();
        resampleStream.lineStart = lineStart;
      }
    };
    function point(x3, y3) {
      x3 = project(x3, y3);
      stream.point(x3[0], x3[1]);
    }
    function lineStart() {
      x06 = NaN;
      resampleStream.point = linePoint2;
      stream.lineStart();
    }
    function linePoint2(lambda, phi) {
      var c3 = cartesian([lambda, phi]), p = project(lambda, phi);
      resampleLineTo(x06, y06, lambda04, a0, b0, c0, x06 = p[0], y06 = p[1], lambda04 = lambda, a0 = c3[0], b0 = c3[1], c0 = c3[2], maxDepth, stream);
      stream.point(x06, y06);
    }
    function lineEnd() {
      resampleStream.point = point;
      stream.lineEnd();
    }
    function ringStart() {
      lineStart();
      resampleStream.point = ringPoint;
      resampleStream.lineEnd = ringEnd;
    }
    function ringPoint(lambda, phi) {
      linePoint2(lambda004 = lambda, phi), x004 = x06, y004 = y06, a00 = a0, b00 = b0, c00 = c0;
      resampleStream.point = linePoint2;
    }
    function ringEnd() {
      resampleLineTo(x06, y06, lambda04, a0, b0, c0, x004, y004, lambda004, a00, b00, c00, maxDepth, stream);
      resampleStream.lineEnd = lineEnd;
      lineEnd();
    }
    return resampleStream;
  };
}

// node_modules/d3-geo/src/projection/index.js
var transformRadians = transformer({
  point: function(x3, y3) {
    this.stream.point(x3 * radians, y3 * radians);
  }
});
function transformRotate(rotate) {
  return transformer({
    point: function(x3, y3) {
      var r3 = rotate(x3, y3);
      return this.stream.point(r3[0], r3[1]);
    }
  });
}
function scaleTranslate(k3, dx, dy, sx, sy) {
  function transform(x3, y3) {
    x3 *= sx;
    y3 *= sy;
    return [dx + k3 * x3, dy - k3 * y3];
  }
  transform.invert = function(x3, y3) {
    return [(x3 - dx) / k3 * sx, (dy - y3) / k3 * sy];
  };
  return transform;
}
function scaleTranslateRotate(k3, dx, dy, sx, sy, alpha) {
  if (!alpha) return scaleTranslate(k3, dx, dy, sx, sy);
  var cosAlpha = cos(alpha), sinAlpha = sin(alpha), a3 = cosAlpha * k3, b2 = sinAlpha * k3, ai = cosAlpha / k3, bi = sinAlpha / k3, ci = (sinAlpha * dy - cosAlpha * dx) / k3, fi = (sinAlpha * dx + cosAlpha * dy) / k3;
  function transform(x3, y3) {
    x3 *= sx;
    y3 *= sy;
    return [a3 * x3 - b2 * y3 + dx, dy - b2 * x3 - a3 * y3];
  }
  transform.invert = function(x3, y3) {
    return [sx * (ai * x3 - bi * y3 + ci), sy * (fi - bi * x3 - ai * y3)];
  };
  return transform;
}
function projection(project) {
  return projectionMutator(function() {
    return project;
  })();
}
function projectionMutator(projectAt) {
  var project, k3 = 150, x3 = 480, y3 = 250, lambda = 0, phi = 0, deltaLambda = 0, deltaPhi = 0, deltaGamma = 0, rotate, alpha = 0, sx = 1, sy = 1, theta = null, preclip = antimeridian_default, x06 = null, y06, x12, y12, postclip = identity_default, delta2 = 0.5, projectResample, projectTransform, projectRotateTransform, cache, cacheStream;
  function projection2(point) {
    return projectRotateTransform(point[0] * radians, point[1] * radians);
  }
  function invert(point) {
    point = projectRotateTransform.invert(point[0], point[1]);
    return point && [point[0] * degrees, point[1] * degrees];
  }
  projection2.stream = function(stream) {
    return cache && cacheStream === stream ? cache : cache = transformRadians(transformRotate(rotate)(preclip(projectResample(postclip(cacheStream = stream)))));
  };
  projection2.preclip = function(_) {
    return arguments.length ? (preclip = _, theta = void 0, reset()) : preclip;
  };
  projection2.postclip = function(_) {
    return arguments.length ? (postclip = _, x06 = y06 = x12 = y12 = null, reset()) : postclip;
  };
  projection2.clipAngle = function(_) {
    return arguments.length ? (preclip = +_ ? circle_default2(theta = _ * radians) : (theta = null, antimeridian_default), reset()) : theta * degrees;
  };
  projection2.clipExtent = function(_) {
    return arguments.length ? (postclip = _ == null ? (x06 = y06 = x12 = y12 = null, identity_default) : clipRectangle(x06 = +_[0][0], y06 = +_[0][1], x12 = +_[1][0], y12 = +_[1][1]), reset()) : x06 == null ? null : [[x06, y06], [x12, y12]];
  };
  projection2.scale = function(_) {
    return arguments.length ? (k3 = +_, recenter()) : k3;
  };
  projection2.translate = function(_) {
    return arguments.length ? (x3 = +_[0], y3 = +_[1], recenter()) : [x3, y3];
  };
  projection2.center = function(_) {
    return arguments.length ? (lambda = _[0] % 360 * radians, phi = _[1] % 360 * radians, recenter()) : [lambda * degrees, phi * degrees];
  };
  projection2.rotate = function(_) {
    return arguments.length ? (deltaLambda = _[0] % 360 * radians, deltaPhi = _[1] % 360 * radians, deltaGamma = _.length > 2 ? _[2] % 360 * radians : 0, recenter()) : [deltaLambda * degrees, deltaPhi * degrees, deltaGamma * degrees];
  };
  projection2.angle = function(_) {
    return arguments.length ? (alpha = _ % 360 * radians, recenter()) : alpha * degrees;
  };
  projection2.reflectX = function(_) {
    return arguments.length ? (sx = _ ? -1 : 1, recenter()) : sx < 0;
  };
  projection2.reflectY = function(_) {
    return arguments.length ? (sy = _ ? -1 : 1, recenter()) : sy < 0;
  };
  projection2.precision = function(_) {
    return arguments.length ? (projectResample = resample_default(projectTransform, delta2 = _ * _), reset()) : sqrt(delta2);
  };
  projection2.fitExtent = function(extent, object3) {
    return fitExtent(projection2, extent, object3);
  };
  projection2.fitSize = function(size, object3) {
    return fitSize(projection2, size, object3);
  };
  projection2.fitWidth = function(width, object3) {
    return fitWidth(projection2, width, object3);
  };
  projection2.fitHeight = function(height, object3) {
    return fitHeight(projection2, height, object3);
  };
  function recenter() {
    var center = scaleTranslateRotate(k3, 0, 0, sx, sy, alpha).apply(null, project(lambda, phi)), transform = scaleTranslateRotate(k3, x3 - center[0], y3 - center[1], sx, sy, alpha);
    rotate = rotateRadians(deltaLambda, deltaPhi, deltaGamma);
    projectTransform = compose_default(project, transform);
    projectRotateTransform = compose_default(rotate, projectTransform);
    projectResample = resample_default(projectTransform, delta2);
    return reset();
  }
  function reset() {
    cache = cacheStream = null;
    return projection2;
  }
  return function() {
    project = projectAt.apply(this, arguments);
    projection2.invert = project.invert && invert;
    return recenter();
  };
}

// node_modules/d3-geo/src/projection/conic.js
function conicProjection(projectAt) {
  var phi02 = 0, phi12 = pi / 3, m = projectionMutator(projectAt), p = m(phi02, phi12);
  p.parallels = function(_) {
    return arguments.length ? m(phi02 = _[0] * radians, phi12 = _[1] * radians) : [phi02 * degrees, phi12 * degrees];
  };
  return p;
}

// node_modules/d3-geo/src/projection/cylindricalEqualArea.js
function cylindricalEqualAreaRaw(phi02) {
  var cosPhi03 = cos(phi02);
  function forward(lambda, phi) {
    return [lambda * cosPhi03, sin(phi) / cosPhi03];
  }
  forward.invert = function(x3, y3) {
    return [x3 / cosPhi03, asin(y3 * cosPhi03)];
  };
  return forward;
}

// node_modules/d3-geo/src/projection/conicEqualArea.js
function conicEqualAreaRaw(y06, y12) {
  var sy0 = sin(y06), n3 = (sy0 + sin(y12)) / 2;
  if (abs(n3) < epsilon) return cylindricalEqualAreaRaw(y06);
  var c3 = 1 + sy0 * (2 * n3 - sy0), r0 = sqrt(c3) / n3;
  function project(x3, y3) {
    var r3 = sqrt(c3 - 2 * n3 * sin(y3)) / n3;
    return [r3 * sin(x3 *= n3), r0 - r3 * cos(x3)];
  }
  project.invert = function(x3, y3) {
    var r0y = r0 - y3, l3 = atan2(x3, abs(r0y)) * sign(r0y);
    if (r0y * n3 < 0)
      l3 -= pi * sign(x3) * sign(r0y);
    return [l3 / n3, asin((c3 - (x3 * x3 + r0y * r0y) * n3 * n3) / (2 * n3))];
  };
  return project;
}
function conicEqualArea_default() {
  return conicProjection(conicEqualAreaRaw).scale(155.424).center([0, 33.6442]);
}

// node_modules/d3-geo/src/projection/albers.js
function albers_default() {
  return conicEqualArea_default().parallels([29.5, 45.5]).scale(1070).translate([480, 250]).rotate([96, 0]).center([-0.6, 38.7]);
}

// node_modules/d3-geo/src/projection/albersUsa.js
function multiplex(streams) {
  var n3 = streams.length;
  return {
    point: function(x3, y3) {
      var i2 = -1;
      while (++i2 < n3) streams[i2].point(x3, y3);
    },
    sphere: function() {
      var i2 = -1;
      while (++i2 < n3) streams[i2].sphere();
    },
    lineStart: function() {
      var i2 = -1;
      while (++i2 < n3) streams[i2].lineStart();
    },
    lineEnd: function() {
      var i2 = -1;
      while (++i2 < n3) streams[i2].lineEnd();
    },
    polygonStart: function() {
      var i2 = -1;
      while (++i2 < n3) streams[i2].polygonStart();
    },
    polygonEnd: function() {
      var i2 = -1;
      while (++i2 < n3) streams[i2].polygonEnd();
    }
  };
}
function albersUsa_default() {
  var cache, cacheStream, lower48 = albers_default(), lower48Point, alaska = conicEqualArea_default().rotate([154, 0]).center([-2, 58.5]).parallels([55, 65]), alaskaPoint, hawaii = conicEqualArea_default().rotate([157, 0]).center([-3, 19.9]).parallels([8, 18]), hawaiiPoint, point, pointStream = { point: function(x3, y3) {
    point = [x3, y3];
  } };
  function albersUsa(coordinates2) {
    var x3 = coordinates2[0], y3 = coordinates2[1];
    return point = null, (lower48Point.point(x3, y3), point) || (alaskaPoint.point(x3, y3), point) || (hawaiiPoint.point(x3, y3), point);
  }
  albersUsa.invert = function(coordinates2) {
    var k3 = lower48.scale(), t3 = lower48.translate(), x3 = (coordinates2[0] - t3[0]) / k3, y3 = (coordinates2[1] - t3[1]) / k3;
    return (y3 >= 0.12 && y3 < 0.234 && x3 >= -0.425 && x3 < -0.214 ? alaska : y3 >= 0.166 && y3 < 0.234 && x3 >= -0.214 && x3 < -0.115 ? hawaii : lower48).invert(coordinates2);
  };
  albersUsa.stream = function(stream) {
    return cache && cacheStream === stream ? cache : cache = multiplex([lower48.stream(cacheStream = stream), alaska.stream(stream), hawaii.stream(stream)]);
  };
  albersUsa.precision = function(_) {
    if (!arguments.length) return lower48.precision();
    lower48.precision(_), alaska.precision(_), hawaii.precision(_);
    return reset();
  };
  albersUsa.scale = function(_) {
    if (!arguments.length) return lower48.scale();
    lower48.scale(_), alaska.scale(_ * 0.35), hawaii.scale(_);
    return albersUsa.translate(lower48.translate());
  };
  albersUsa.translate = function(_) {
    if (!arguments.length) return lower48.translate();
    var k3 = lower48.scale(), x3 = +_[0], y3 = +_[1];
    lower48Point = lower48.translate(_).clipExtent([[x3 - 0.455 * k3, y3 - 0.238 * k3], [x3 + 0.455 * k3, y3 + 0.238 * k3]]).stream(pointStream);
    alaskaPoint = alaska.translate([x3 - 0.307 * k3, y3 + 0.201 * k3]).clipExtent([[x3 - 0.425 * k3 + epsilon, y3 + 0.12 * k3 + epsilon], [x3 - 0.214 * k3 - epsilon, y3 + 0.234 * k3 - epsilon]]).stream(pointStream);
    hawaiiPoint = hawaii.translate([x3 - 0.205 * k3, y3 + 0.212 * k3]).clipExtent([[x3 - 0.214 * k3 + epsilon, y3 + 0.166 * k3 + epsilon], [x3 - 0.115 * k3 - epsilon, y3 + 0.234 * k3 - epsilon]]).stream(pointStream);
    return reset();
  };
  albersUsa.fitExtent = function(extent, object3) {
    return fitExtent(albersUsa, extent, object3);
  };
  albersUsa.fitSize = function(size, object3) {
    return fitSize(albersUsa, size, object3);
  };
  albersUsa.fitWidth = function(width, object3) {
    return fitWidth(albersUsa, width, object3);
  };
  albersUsa.fitHeight = function(height, object3) {
    return fitHeight(albersUsa, height, object3);
  };
  function reset() {
    cache = cacheStream = null;
    return albersUsa;
  }
  return albersUsa.scale(1070);
}

// node_modules/d3-geo/src/projection/azimuthal.js
function azimuthalRaw(scale) {
  return function(x3, y3) {
    var cx = cos(x3), cy = cos(y3), k3 = scale(cx * cy);
    if (k3 === Infinity) return [2, 0];
    return [
      k3 * cy * sin(x3),
      k3 * sin(y3)
    ];
  };
}
function azimuthalInvert(angle2) {
  return function(x3, y3) {
    var z = sqrt(x3 * x3 + y3 * y3), c3 = angle2(z), sc = sin(c3), cc = cos(c3);
    return [
      atan2(x3 * sc, z * cc),
      asin(z && y3 * sc / z)
    ];
  };
}

// node_modules/d3-geo/src/projection/azimuthalEqualArea.js
var azimuthalEqualAreaRaw = azimuthalRaw(function(cxcy) {
  return sqrt(2 / (1 + cxcy));
});
azimuthalEqualAreaRaw.invert = azimuthalInvert(function(z) {
  return 2 * asin(z / 2);
});
function azimuthalEqualArea_default() {
  return projection(azimuthalEqualAreaRaw).scale(124.75).clipAngle(180 - 1e-3);
}

// node_modules/d3-geo/src/projection/azimuthalEquidistant.js
var azimuthalEquidistantRaw = azimuthalRaw(function(c3) {
  return (c3 = acos(c3)) && c3 / sin(c3);
});
azimuthalEquidistantRaw.invert = azimuthalInvert(function(z) {
  return z;
});
function azimuthalEquidistant_default() {
  return projection(azimuthalEquidistantRaw).scale(79.4188).clipAngle(180 - 1e-3);
}

// node_modules/d3-geo/src/projection/mercator.js
function mercatorRaw(lambda, phi) {
  return [lambda, log(tan((halfPi + phi) / 2))];
}
mercatorRaw.invert = function(x3, y3) {
  return [x3, 2 * atan(exp(y3)) - halfPi];
};
function mercator_default() {
  return mercatorProjection(mercatorRaw).scale(961 / tau);
}
function mercatorProjection(project) {
  var m = projection(project), center = m.center, scale = m.scale, translate = m.translate, clipExtent = m.clipExtent, x06 = null, y06, x12, y12;
  m.scale = function(_) {
    return arguments.length ? (scale(_), reclip()) : scale();
  };
  m.translate = function(_) {
    return arguments.length ? (translate(_), reclip()) : translate();
  };
  m.center = function(_) {
    return arguments.length ? (center(_), reclip()) : center();
  };
  m.clipExtent = function(_) {
    return arguments.length ? (_ == null ? x06 = y06 = x12 = y12 = null : (x06 = +_[0][0], y06 = +_[0][1], x12 = +_[1][0], y12 = +_[1][1]), reclip()) : x06 == null ? null : [[x06, y06], [x12, y12]];
  };
  function reclip() {
    var k3 = pi * scale(), t3 = m(rotation_default(m.rotate()).invert([0, 0]));
    return clipExtent(x06 == null ? [[t3[0] - k3, t3[1] - k3], [t3[0] + k3, t3[1] + k3]] : project === mercatorRaw ? [[Math.max(t3[0] - k3, x06), y06], [Math.min(t3[0] + k3, x12), y12]] : [[x06, Math.max(t3[1] - k3, y06)], [x12, Math.min(t3[1] + k3, y12)]]);
  }
  return reclip();
}

// node_modules/d3-geo/src/projection/conicConformal.js
function tany(y3) {
  return tan((halfPi + y3) / 2);
}
function conicConformalRaw(y06, y12) {
  var cy0 = cos(y06), n3 = y06 === y12 ? sin(y06) : log(cy0 / cos(y12)) / log(tany(y12) / tany(y06)), f3 = cy0 * pow(tany(y06), n3) / n3;
  if (!n3) return mercatorRaw;
  function project(x3, y3) {
    if (f3 > 0) {
      if (y3 < -halfPi + epsilon) y3 = -halfPi + epsilon;
    } else {
      if (y3 > halfPi - epsilon) y3 = halfPi - epsilon;
    }
    var r3 = f3 / pow(tany(y3), n3);
    return [r3 * sin(n3 * x3), f3 - r3 * cos(n3 * x3)];
  }
  project.invert = function(x3, y3) {
    var fy = f3 - y3, r3 = sign(n3) * sqrt(x3 * x3 + fy * fy), l3 = atan2(x3, abs(fy)) * sign(fy);
    if (fy * n3 < 0)
      l3 -= pi * sign(x3) * sign(fy);
    return [l3 / n3, 2 * atan(pow(f3 / r3, 1 / n3)) - halfPi];
  };
  return project;
}
function conicConformal_default() {
  return conicProjection(conicConformalRaw).scale(109.5).parallels([30, 30]);
}

// node_modules/d3-geo/src/projection/equirectangular.js
function equirectangularRaw(lambda, phi) {
  return [lambda, phi];
}
equirectangularRaw.invert = equirectangularRaw;
function equirectangular_default() {
  return projection(equirectangularRaw).scale(152.63);
}

// node_modules/d3-geo/src/projection/conicEquidistant.js
function conicEquidistantRaw(y06, y12) {
  var cy0 = cos(y06), n3 = y06 === y12 ? sin(y06) : (cy0 - cos(y12)) / (y12 - y06), g2 = cy0 / n3 + y06;
  if (abs(n3) < epsilon) return equirectangularRaw;
  function project(x3, y3) {
    var gy = g2 - y3, nx = n3 * x3;
    return [gy * sin(nx), g2 - gy * cos(nx)];
  }
  project.invert = function(x3, y3) {
    var gy = g2 - y3, l3 = atan2(x3, abs(gy)) * sign(gy);
    if (gy * n3 < 0)
      l3 -= pi * sign(x3) * sign(gy);
    return [l3 / n3, g2 - sign(n3) * sqrt(x3 * x3 + gy * gy)];
  };
  return project;
}
function conicEquidistant_default() {
  return conicProjection(conicEquidistantRaw).scale(131.154).center([0, 13.9389]);
}

// node_modules/d3-geo/src/projection/equalEarth.js
var A1 = 1.340264;
var A2 = -0.081106;
var A3 = 893e-6;
var A4 = 3796e-6;
var M = sqrt(3) / 2;
var iterations = 12;
function equalEarthRaw(lambda, phi) {
  var l3 = asin(M * sin(phi)), l22 = l3 * l3, l6 = l22 * l22 * l22;
  return [
    lambda * cos(l3) / (M * (A1 + 3 * A2 * l22 + l6 * (7 * A3 + 9 * A4 * l22))),
    l3 * (A1 + A2 * l22 + l6 * (A3 + A4 * l22))
  ];
}
equalEarthRaw.invert = function(x3, y3) {
  var l3 = y3, l22 = l3 * l3, l6 = l22 * l22 * l22;
  for (var i2 = 0, delta, fy, fpy; i2 < iterations; ++i2) {
    fy = l3 * (A1 + A2 * l22 + l6 * (A3 + A4 * l22)) - y3;
    fpy = A1 + 3 * A2 * l22 + l6 * (7 * A3 + 9 * A4 * l22);
    l3 -= delta = fy / fpy, l22 = l3 * l3, l6 = l22 * l22 * l22;
    if (abs(delta) < epsilon2) break;
  }
  return [
    M * x3 * (A1 + 3 * A2 * l22 + l6 * (7 * A3 + 9 * A4 * l22)) / cos(l3),
    asin(sin(l3) / M)
  ];
};
function equalEarth_default() {
  return projection(equalEarthRaw).scale(177.158);
}

// node_modules/d3-geo/src/projection/gnomonic.js
function gnomonicRaw(x3, y3) {
  var cy = cos(y3), k3 = cos(x3) * cy;
  return [cy * sin(x3) / k3, sin(y3) / k3];
}
gnomonicRaw.invert = azimuthalInvert(atan);
function gnomonic_default() {
  return projection(gnomonicRaw).scale(144.049).clipAngle(60);
}

// node_modules/d3-geo/src/projection/identity.js
function identity_default2() {
  var k3 = 1, tx = 0, ty = 0, sx = 1, sy = 1, alpha = 0, ca, sa, x06 = null, y06, x12, y12, kx = 1, ky = 1, transform = transformer({
    point: function(x3, y3) {
      var p = projection2([x3, y3]);
      this.stream.point(p[0], p[1]);
    }
  }), postclip = identity_default, cache, cacheStream;
  function reset() {
    kx = k3 * sx;
    ky = k3 * sy;
    cache = cacheStream = null;
    return projection2;
  }
  function projection2(p) {
    var x3 = p[0] * kx, y3 = p[1] * ky;
    if (alpha) {
      var t3 = y3 * ca - x3 * sa;
      x3 = x3 * ca + y3 * sa;
      y3 = t3;
    }
    return [x3 + tx, y3 + ty];
  }
  projection2.invert = function(p) {
    var x3 = p[0] - tx, y3 = p[1] - ty;
    if (alpha) {
      var t3 = y3 * ca + x3 * sa;
      x3 = x3 * ca - y3 * sa;
      y3 = t3;
    }
    return [x3 / kx, y3 / ky];
  };
  projection2.stream = function(stream) {
    return cache && cacheStream === stream ? cache : cache = transform(postclip(cacheStream = stream));
  };
  projection2.postclip = function(_) {
    return arguments.length ? (postclip = _, x06 = y06 = x12 = y12 = null, reset()) : postclip;
  };
  projection2.clipExtent = function(_) {
    return arguments.length ? (postclip = _ == null ? (x06 = y06 = x12 = y12 = null, identity_default) : clipRectangle(x06 = +_[0][0], y06 = +_[0][1], x12 = +_[1][0], y12 = +_[1][1]), reset()) : x06 == null ? null : [[x06, y06], [x12, y12]];
  };
  projection2.scale = function(_) {
    return arguments.length ? (k3 = +_, reset()) : k3;
  };
  projection2.translate = function(_) {
    return arguments.length ? (tx = +_[0], ty = +_[1], reset()) : [tx, ty];
  };
  projection2.angle = function(_) {
    return arguments.length ? (alpha = _ % 360 * radians, sa = sin(alpha), ca = cos(alpha), reset()) : alpha * degrees;
  };
  projection2.reflectX = function(_) {
    return arguments.length ? (sx = _ ? -1 : 1, reset()) : sx < 0;
  };
  projection2.reflectY = function(_) {
    return arguments.length ? (sy = _ ? -1 : 1, reset()) : sy < 0;
  };
  projection2.fitExtent = function(extent, object3) {
    return fitExtent(projection2, extent, object3);
  };
  projection2.fitSize = function(size, object3) {
    return fitSize(projection2, size, object3);
  };
  projection2.fitWidth = function(width, object3) {
    return fitWidth(projection2, width, object3);
  };
  projection2.fitHeight = function(height, object3) {
    return fitHeight(projection2, height, object3);
  };
  return projection2;
}

// node_modules/d3-geo/src/projection/naturalEarth1.js
function naturalEarth1Raw(lambda, phi) {
  var phi2 = phi * phi, phi4 = phi2 * phi2;
  return [
    lambda * (0.8707 - 0.131979 * phi2 + phi4 * (-0.013791 + phi4 * (3971e-6 * phi2 - 1529e-6 * phi4))),
    phi * (1.007226 + phi2 * (0.015085 + phi4 * (-0.044475 + 0.028874 * phi2 - 5916e-6 * phi4)))
  ];
}
naturalEarth1Raw.invert = function(x3, y3) {
  var phi = y3, i2 = 25, delta;
  do {
    var phi2 = phi * phi, phi4 = phi2 * phi2;
    phi -= delta = (phi * (1.007226 + phi2 * (0.015085 + phi4 * (-0.044475 + 0.028874 * phi2 - 5916e-6 * phi4))) - y3) / (1.007226 + phi2 * (0.015085 * 3 + phi4 * (-0.044475 * 7 + 0.028874 * 9 * phi2 - 5916e-6 * 11 * phi4)));
  } while (abs(delta) > epsilon && --i2 > 0);
  return [
    x3 / (0.8707 + (phi2 = phi * phi) * (-0.131979 + phi2 * (-0.013791 + phi2 * phi2 * phi2 * (3971e-6 - 1529e-6 * phi2)))),
    phi
  ];
};
function naturalEarth1_default() {
  return projection(naturalEarth1Raw).scale(175.295);
}

// node_modules/d3-geo/src/projection/orthographic.js
function orthographicRaw(x3, y3) {
  return [cos(y3) * sin(x3), sin(y3)];
}
orthographicRaw.invert = azimuthalInvert(asin);
function orthographic_default() {
  return projection(orthographicRaw).scale(249.5).clipAngle(90 + epsilon);
}

// node_modules/d3-geo/src/projection/stereographic.js
function stereographicRaw(x3, y3) {
  var cy = cos(y3), k3 = 1 + cos(x3) * cy;
  return [cy * sin(x3) / k3, sin(y3) / k3];
}
stereographicRaw.invert = azimuthalInvert(function(z) {
  return 2 * atan(z);
});
function stereographic_default() {
  return projection(stereographicRaw).scale(250).clipAngle(142);
}

// node_modules/d3-geo/src/projection/transverseMercator.js
function transverseMercatorRaw(lambda, phi) {
  return [log(tan((halfPi + phi) / 2)), -lambda];
}
transverseMercatorRaw.invert = function(x3, y3) {
  return [-y3, 2 * atan(exp(x3)) - halfPi];
};
function transverseMercator_default() {
  var m = mercatorProjection(transverseMercatorRaw), center = m.center, rotate = m.rotate;
  m.center = function(_) {
    return arguments.length ? center([-_[1], _[0]]) : (_ = center(), [_[1], -_[0]]);
  };
  m.rotate = function(_) {
    return arguments.length ? rotate([_[0], _[1], _.length > 2 ? _[2] + 90 : 90]) : (_ = rotate(), [_[0], _[1], _[2] - 90]);
  };
  return rotate([0, 0, 90]).scale(159.155);
}

// node_modules/topojson-client/src/identity.js
function identity_default3(x3) {
  return x3;
}

// node_modules/topojson-client/src/transform.js
function transform_default2(transform) {
  if (transform == null) return identity_default3;
  var x06, y06, kx = transform.scale[0], ky = transform.scale[1], dx = transform.translate[0], dy = transform.translate[1];
  return function(input, i2) {
    if (!i2) x06 = y06 = 0;
    var j2 = 2, n3 = input.length, output = new Array(n3);
    output[0] = (x06 += input[0]) * kx + dx;
    output[1] = (y06 += input[1]) * ky + dy;
    while (j2 < n3) output[j2] = input[j2], ++j2;
    return output;
  };
}

// node_modules/topojson-client/src/reverse.js
function reverse_default(array, n3) {
  var t3, j2 = array.length, i2 = j2 - n3;
  while (i2 < --j2) t3 = array[i2], array[i2++] = array[j2], array[j2] = t3;
}

// node_modules/topojson-client/src/feature.js
function feature_default(topology, o3) {
  if (typeof o3 === "string") o3 = topology.objects[o3];
  return o3.type === "GeometryCollection" ? { type: "FeatureCollection", features: o3.geometries.map(function(o4) {
    return feature(topology, o4);
  }) } : feature(topology, o3);
}
function feature(topology, o3) {
  var id = o3.id, bbox = o3.bbox, properties = o3.properties == null ? {} : o3.properties, geometry = object2(topology, o3);
  return id == null && bbox == null ? { type: "Feature", properties, geometry } : bbox == null ? { type: "Feature", id, properties, geometry } : { type: "Feature", id, bbox, properties, geometry };
}
function object2(topology, o3) {
  var transformPoint = transform_default2(topology.transform), arcs = topology.arcs;
  function arc(i2, points) {
    if (points.length) points.pop();
    for (var a3 = arcs[i2 < 0 ? ~i2 : i2], k3 = 0, n3 = a3.length; k3 < n3; ++k3) {
      points.push(transformPoint(a3[k3], k3));
    }
    if (i2 < 0) reverse_default(points, n3);
  }
  function point(p) {
    return transformPoint(p);
  }
  function line(arcs2) {
    var points = [];
    for (var i2 = 0, n3 = arcs2.length; i2 < n3; ++i2) arc(arcs2[i2], points);
    if (points.length < 2) points.push(points[0]);
    return points;
  }
  function ring(arcs2) {
    var points = line(arcs2);
    while (points.length < 4) points.push(points[0]);
    return points;
  }
  function polygon(arcs2) {
    return arcs2.map(ring);
  }
  function geometry(o4) {
    var type = o4.type, coordinates2;
    switch (type) {
      case "GeometryCollection":
        return { type, geometries: o4.geometries.map(geometry) };
      case "Point":
        coordinates2 = point(o4.coordinates);
        break;
      case "MultiPoint":
        coordinates2 = o4.coordinates.map(point);
        break;
      case "LineString":
        coordinates2 = line(o4.arcs);
        break;
      case "MultiLineString":
        coordinates2 = o4.arcs.map(line);
        break;
      case "Polygon":
        coordinates2 = polygon(o4.arcs);
        break;
      case "MultiPolygon":
        coordinates2 = o4.arcs.map(polygon);
        break;
      default:
        return null;
    }
    return { type, coordinates: coordinates2 };
  }
  return geometry(o3);
}

// node_modules/topojson-client/src/stitch.js
function stitch_default(topology, arcs) {
  var stitchedArcs = {}, fragmentByStart = {}, fragmentByEnd = {}, fragments = [], emptyIndex = -1;
  arcs.forEach(function(i2, j2) {
    var arc = topology.arcs[i2 < 0 ? ~i2 : i2], t3;
    if (arc.length < 3 && !arc[1][0] && !arc[1][1]) {
      t3 = arcs[++emptyIndex], arcs[emptyIndex] = i2, arcs[j2] = t3;
    }
  });
  arcs.forEach(function(i2) {
    var e3 = ends(i2), start = e3[0], end = e3[1], f3, g2;
    if (f3 = fragmentByEnd[start]) {
      delete fragmentByEnd[f3.end];
      f3.push(i2);
      f3.end = end;
      if (g2 = fragmentByStart[end]) {
        delete fragmentByStart[g2.start];
        var fg = g2 === f3 ? f3 : f3.concat(g2);
        fragmentByStart[fg.start = f3.start] = fragmentByEnd[fg.end = g2.end] = fg;
      } else {
        fragmentByStart[f3.start] = fragmentByEnd[f3.end] = f3;
      }
    } else if (f3 = fragmentByStart[end]) {
      delete fragmentByStart[f3.start];
      f3.unshift(i2);
      f3.start = start;
      if (g2 = fragmentByEnd[start]) {
        delete fragmentByEnd[g2.end];
        var gf = g2 === f3 ? f3 : g2.concat(f3);
        fragmentByStart[gf.start = g2.start] = fragmentByEnd[gf.end = f3.end] = gf;
      } else {
        fragmentByStart[f3.start] = fragmentByEnd[f3.end] = f3;
      }
    } else {
      f3 = [i2];
      fragmentByStart[f3.start = start] = fragmentByEnd[f3.end = end] = f3;
    }
  });
  function ends(i2) {
    var arc = topology.arcs[i2 < 0 ? ~i2 : i2], p02 = arc[0], p1;
    if (topology.transform) p1 = [0, 0], arc.forEach(function(dp) {
      p1[0] += dp[0], p1[1] += dp[1];
    });
    else p1 = arc[arc.length - 1];
    return i2 < 0 ? [p1, p02] : [p02, p1];
  }
  function flush(fragmentByEnd2, fragmentByStart2) {
    for (var k3 in fragmentByEnd2) {
      var f3 = fragmentByEnd2[k3];
      delete fragmentByStart2[f3.start];
      delete f3.start;
      delete f3.end;
      f3.forEach(function(i2) {
        stitchedArcs[i2 < 0 ? ~i2 : i2] = 1;
      });
      fragments.push(f3);
    }
  }
  flush(fragmentByEnd, fragmentByStart);
  flush(fragmentByStart, fragmentByEnd);
  arcs.forEach(function(i2) {
    if (!stitchedArcs[i2 < 0 ? ~i2 : i2]) fragments.push([i2]);
  });
  return fragments;
}

// node_modules/topojson-client/src/mesh.js
function mesh_default(topology) {
  return object2(topology, meshArcs.apply(this, arguments));
}
function meshArcs(topology, object3, filter) {
  var arcs, i2, n3;
  if (arguments.length > 1) arcs = extractArcs(topology, object3, filter);
  else for (i2 = 0, arcs = new Array(n3 = topology.arcs.length); i2 < n3; ++i2) arcs[i2] = i2;
  return { type: "MultiLineString", arcs: stitch_default(topology, arcs) };
}
function extractArcs(topology, object3, filter) {
  var arcs = [], geomsByArc = [], geom;
  function extract0(i2) {
    var j2 = i2 < 0 ? ~i2 : i2;
    (geomsByArc[j2] || (geomsByArc[j2] = [])).push({ i: i2, g: geom });
  }
  function extract1(arcs2) {
    arcs2.forEach(extract0);
  }
  function extract2(arcs2) {
    arcs2.forEach(extract1);
  }
  function extract3(arcs2) {
    arcs2.forEach(extract2);
  }
  function geometry(o3) {
    switch (geom = o3, o3.type) {
      case "GeometryCollection":
        o3.geometries.forEach(geometry);
        break;
      case "LineString":
        extract1(o3.arcs);
        break;
      case "MultiLineString":
      case "Polygon":
        extract2(o3.arcs);
        break;
      case "MultiPolygon":
        extract3(o3.arcs);
        break;
    }
  }
  geometry(object3);
  geomsByArc.forEach(filter == null ? function(geoms) {
    arcs.push(geoms[0].i);
  } : function(geoms) {
    if (filter(geoms[0].g, geoms[geoms.length - 1].g)) arcs.push(geoms[0].i);
  });
  return arcs;
}

// node_modules/react-simple-maps/dist/shared/JKVre3Xc.es.js
var { geoPath: g, ...d } = src_exports;
var f = d;
var y = (0, import_react.createContext)(void 0);
var b = ({ width: r3 = 800, height: a3 = 600, projection: n3 = "geoEqualEarth", projectionConfig: s2 = {}, children: i2 }) => {
  const [c3, l3] = s2.center || [], [p, h, m] = s2.rotate || [], [u, d3] = s2.parallels || [], b2 = s2.scale || null, j2 = (0, import_react.useMemo)(() => (({ projectionConfig: e3 = {}, projection: r4 = "geoEqualEarth", width: t3 = 800, height: o3 = 600 }) => {
    if ("function" == typeof r4) return r4;
    const a4 = f[r4]().translate([t3 / 2, o3 / 2]);
    if (e3.center && a4.center(e3.center), e3.rotate) {
      const [r5, t4, o4] = e3.rotate;
      a4.rotate(void 0 === o4 ? [r5, t4] : [r5, t4, o4]);
    }
    return e3.scale && a4.scale(e3.scale), e3.parallels && function(e4) {
      return "parallels" in e4;
    }(a4) && a4.parallels(e3.parallels), a4;
  })({ projectionConfig: { center: "number" == typeof c3 && "number" == typeof l3 ? [c3, l3] : void 0, rotate: "number" == typeof p && "number" == typeof h ? [p, h, m] : void 0, parallels: "number" == typeof u && "number" == typeof d3 ? [u, d3] : void 0, scale: b2 || void 0 }, projection: n3, width: r3, height: a3 }), [r3, a3, n3, c3, l3, p, h, m, u, d3, b2]), N2 = (0, import_react.useCallback)(j2, [j2]), E3 = (0, import_react.useMemo)(() => ({ width: r3, height: a3, projection: N2, path: g().projection(N2) }), [r3, a3, N2]);
  return import_react.default.createElement(y.Provider, { value: E3 }, i2);
};
var j = () => {
  const e3 = (0, import_react.useContext)(y);
  if (!e3) throw new Error("useMapContext must be used within MapProvider");
  return e3;
};
var N = (0, import_react.forwardRef)(({ width: r3 = 800, height: t3 = 600, projection: o3 = "geoEqualEarth", projectionConfig: a3 = {}, className: n3 = "", children: s2, ...i2 }, c3) => import_react.default.createElement(b, { width: r3, height: t3, projection: o3, projectionConfig: a3 }, import_react.default.createElement("svg", { ref: c3, viewBox: `0 0 ${r3} ${t3}`, className: `rsm-svg ${n3}`, ...i2, children: s2 })));
function E(e3, r3) {
  if (!Array.isArray(e3) && "type" in e3 && "Topology" === e3.type) {
    const t4 = e3.objects[Object.keys(e3.objects)[0]], o3 = feature_default(e3, t4).features;
    return r3 ? r3(o3) : o3;
  }
  const t3 = !Array.isArray(e3) && "features" in e3 ? e3.features : e3;
  return r3 ? r3(t3) : t3;
}
function v(e3) {
  if (Array.isArray(e3) || !("type" in e3) || "Topology" !== e3.type) return null;
  const r3 = e3.objects[Object.keys(e3.objects)[0]];
  return { outline: mesh_default(e3, r3, (e4, r4) => e4 === r4), borders: mesh_default(e3, r3, (e4, r4) => e4 !== r4) };
}
function $(e3, r3) {
  return e3 ? e3.map((e4, t3) => ({ ...e4, rsmKey: `geo-${t3}`, svgPath: r3(e4) })) : [];
}
function w(e3) {
  return "string" == typeof e3;
}
function k({ geography: e3, parseGeographies: r3 }) {
  const { path: o3 } = j(), [a3, n3] = (0, import_react.useState)({}), c3 = w(e3) ? e3 : JSON.stringify(e3);
  (0, import_react.useEffect)(() => {
    var t3;
    "undefined" != typeof window && (e3 && (w(e3) ? (t3 = e3, fetch(t3).then((e4) => {
      if (!e4.ok) throw Error(e4.statusText);
      return e4.json();
    }).catch((e4) => {
      console.log("There was a problem when fetching the data: ", e4);
    })).then((e4) => {
      e4 && n3({ geographies: E(e4, r3), mesh: v(e4) });
    }) : n3({ geographies: E(e3, r3), mesh: v(e3) })));
  }, [c3, r3]);
  const { geographies: l3, outline: p, borders: h } = (0, import_react.useMemo)(() => {
    var _a, _b;
    const e4 = function(e5, r4, t3) {
      return e5 && r4 ? { outline: { ...e5, rsmKey: "outline", svgPath: t3(e5) }, borders: { ...r4, rsmKey: "borders", svgPath: t3(r4) } } : {};
    }((_a = a3.mesh) == null ? void 0 : _a.outline, (_b = a3.mesh) == null ? void 0 : _b.borders, o3);
    return { geographies: $(a3.geographies, o3), outline: e4.outline, borders: e4.borders };
  }, [a3, o3]);
  return { geographies: l3, outline: p, borders: h };
}
N.displayName = "ComposableMap";
var A = (0, import_react.forwardRef)(({ geography: r3, children: t3, parseGeographies: o3, className: a3 = "", ...n3 }, s2) => {
  const { path: i2, projection: c3 } = j(), { geographies: l3, outline: p, borders: h } = k({ geography: r3, parseGeographies: o3 });
  return import_react.default.createElement("g", { ref: s2, className: `rsm-geographies ${a3}`, ...n3 }, l3 && l3.length > 0 && t3({ geographies: l3, outline: p, borders: h, path: i2, projection: c3 }));
});
A.displayName = "Geographies";
var P = (0, import_react.forwardRef)(({ geography: r3, className: t3 = "", ...o3 }, a3) => import_react.default.createElement("path", { ref: a3, tabIndex: 0, className: `rsm-geography ${t3}`, d: r3.svgPath, ...o3 }));
P.displayName = "Geography";
var C = (0, import_react.memo)(P);
var G = (0, import_react.forwardRef)(({ fill: r3 = "transparent", stroke: t3 = "currentcolor", step: o3 = [10, 10], className: a3 = "", ...n3 }, s2) => {
  const { path: i2 } = j();
  return import_react.default.createElement("path", { ref: s2, d: i2(graticule().step(o3)()), fill: r3, stroke: t3, className: `rsm-graticule ${a3}`, ...n3 });
});
G.displayName = "Graticule";
var x = (0, import_react.memo)(G);
var M2 = (0, import_react.forwardRef)(({ id: r3 = "rsm-sphere", fill: o3 = "transparent", stroke: a3 = "currentcolor", className: n3 = "", ...s2 }, i2) => {
  const { path: c3 } = j(), p = (0, import_react.useMemo)(() => c3({ type: "Sphere" }), [c3]);
  return import_react.default.createElement(import_react.Fragment, null, import_react.default.createElement("defs", null, import_react.default.createElement("clipPath", { id: r3 }, import_react.default.createElement("path", { d: p }))), import_react.default.createElement("path", { ref: i2, d: p, fill: o3, stroke: a3, style: { pointerEvents: "none" }, className: `rsm-sphere ${n3}`, ...s2 }));
});
M2.displayName = "Sphere";
var S = (0, import_react.memo)(M2);
var T = (0, import_react.forwardRef)(({ coordinates: r3, children: t3, className: o3 = "", ...a3 }, n3) => {
  const { projection: s2 } = j(), i2 = s2(r3);
  if (!i2) return null;
  const [c3, l3] = i2;
  return import_react.default.createElement("g", { ref: n3, transform: `translate(${c3}, ${l3})`, className: `rsm-marker ${o3}`, ...a3 }, t3);
});
T.displayName = "Marker";
var q = (0, import_react.forwardRef)(({ from: r3 = [0, 0], to: t3 = [0, 0], coordinates: o3, stroke: a3 = "currentcolor", strokeWidth: n3 = 3, fill: s2 = "transparent", className: i2 = "", ...c3 }, l3) => {
  const { path: p } = j(), h = { type: "LineString", coordinates: o3 || [r3, t3] };
  return import_react.default.createElement("path", { ref: l3, d: p(h), className: `rsm-line ${i2}`, stroke: a3, strokeWidth: n3, fill: s2, ...c3 });
});
q.displayName = "Line";
var K = (0, import_react.forwardRef)(({ subject: r3, children: t3, connectorProps: o3, dx: a3 = 30, dy: n3 = 30, curve: s2 = 0, className: i2 = "", ...c3 }, l3) => {
  const { projection: p } = j(), h = p(r3), m = function(e3 = 30, r4 = 30, t4 = 0.5) {
    const o4 = Array.isArray(t4) ? t4 : [t4, t4];
    return `M0,0 Q${-e3 / 2 - e3 / 2 * o4[0]},${-r4 / 2 + r4 / 2 * o4[1]} ${-e3},${-r4}`;
  }(a3, n3, s2);
  if (!h) return null;
  const [u, g2] = h;
  return import_react.default.createElement("g", { ref: l3, transform: `translate(${u + a3}, ${g2 + n3})`, className: `rsm-annotation ${i2}`, ...c3 }, import_react.default.createElement("path", { d: m, fill: "transparent", stroke: "#000", ...o3 }), t3);
});
K.displayName = "Annotation";

// node_modules/react-simple-maps/dist/shared/DbIF5Tqp.es.js
var import_react2 = __toESM(require_react());
var l2 = (0, import_react2.createContext)(void 0);
var f2 = { x: 0, y: 0, k: 1, transformString: "translate(0 0) scale(1)" };
var x2 = ({ value: t3 = f2, children: n3 }) => import_react2.default.createElement(l2.Provider, { value: t3 }, n3);
var v2 = () => {
  const r3 = (0, import_react2.useContext)(l2);
  if (!r3) throw new Error("useZoomPanContext must be used within ZoomPanProvider");
  return r3;
};
function d2(r3, t3, n3) {
  const e3 = (r3 * n3.k - r3) / 2, o3 = (t3 * n3.k - t3) / 2;
  return [r3 / 2 - (e3 + n3.x) / n3.k, t3 / 2 - (o3 + n3.y) / n3.k];
}
function k2(r3, t3, n3, e3, o3, c3) {
  const a3 = r3([e3, o3]);
  if (!a3) return null;
  return { x: t3 / 2 - a3[0] * c3, y: n3 / 2 - a3[1] * c3, k: c3 };
}
function E2({ center: r3 = [0, 0], filterZoomEvent: t3, onMoveStart: n3, onMoveEnd: a3, onMove: l3, translateExtent: f3 = [[-1 / 0, -1 / 0], [1 / 0, 1 / 0]], scaleExtent: x3 = [1, 8], zoom: v3 = 1 }) {
  const { width: E3, height: y3, projection: g2 } = j(), [p, h] = r3, [z, M3] = (0, import_react2.useState)(() => k2(g2, E3, y3, p, h, v3) ?? { x: 0, y: 0, k: 1 }), Z = (0, import_react2.useRef)(null), S2 = (0, import_react2.useRef)(null), w2 = (0, import_react2.useRef)(null), b2 = (0, import_react2.useRef)(false), [P2, $2] = f3, [j2, N2] = P2, [R, C2] = $2, [G2, K2] = x3, q2 = (0, import_react2.useRef)(n3), A5 = (0, import_react2.useRef)(l3), B = (0, import_react2.useRef)(a3), D = (0, import_react2.useRef)(t3);
  return (0, import_react2.useEffect)(() => {
    q2.current = n3, A5.current = l3, B.current = a3, D.current = t3;
  }), (0, import_react2.useEffect)(() => {
    const r4 = S2.current;
    if (!r4) return;
    const t4 = select_default(r4), n4 = zoom_default().extent([[0, 0], [E3, y3]]).filter((r5) => {
      if (D.current) return D.current(r5);
      const t5 = r5;
      return !!r5 && (!t5.ctrlKey && !t5.button);
    }).scaleExtent([G2, K2]).translateExtent([[j2, N2], [R, C2]]).on("start", (r5) => {
      var _a;
      if (!q2.current || b2.current) return;
      const t5 = (_a = g2.invert) == null ? void 0 : _a.call(g2, d2(E3, y3, r5.transform));
      q2.current({ coordinates: t5 ?? void 0, zoom: r5.transform.k }, r5);
    }).on("zoom", (r5) => {
      if (b2.current) return;
      const { transform: t5, sourceEvent: n5 } = r5;
      M3({ x: t5.x, y: t5.y, k: t5.k, dragging: n5 }), A5.current && A5.current({ x: t5.x, y: t5.y, zoom: t5.k, dragging: n5 }, r5);
    }).on("end", (r5) => {
      var _a;
      if (b2.current) return void (b2.current = false);
      const t5 = (_a = g2.invert) == null ? void 0 : _a.call(g2, d2(E3, y3, r5.transform));
      if (t5) {
        const [n5, e3] = t5;
        Z.current = { x: n5, y: e3, k: r5.transform.k };
      }
      B.current && B.current({ coordinates: t5 ?? void 0, zoom: r5.transform.k }, r5);
    });
    w2.current = n4, t4.call(n4);
  }, [E3, y3, j2, N2, R, C2, G2, K2, g2]), (0, import_react2.useEffect)(() => {
    if (Z.current && p === Z.current.x && h === Z.current.y && v3 === Z.current.k) return;
    const r4 = k2(g2, E3, y3, p, h, v3);
    if (!r4) return;
    if (!S2.current || !w2.current) return;
    const t4 = select_default(S2.current);
    b2.current = true, t4.call(w2.current.transform, identity.translate(r4.x, r4.y).scale(r4.k)), M3((t5) => t5.x === r4.x && t5.y === r4.y && t5.k === r4.k ? t5 : r4), Z.current = { x: p, y: h, k: v3 };
  }, [p, h, v3, E3, y3, g2]), { mapRef: S2, position: z, transformString: `translate(${z.x} ${z.y}) scale(${z.k})` };
}
var y2 = (0, import_react2.forwardRef)(({ center: t3 = [0, 0], zoom: n3 = 1, minZoom: e3 = 1, maxZoom: o3 = 8, translateExtent: c3, filterZoomEvent: a3, onMoveStart: u, onMove: i2, onMoveEnd: m, className: l3 = "", children: f3, ...v3 }, d3) => {
  const { width: k3, height: y3 } = j(), { mapRef: g2, transformString: p, position: h } = E2({ center: t3, filterZoomEvent: a3, onMoveStart: u, onMove: i2, onMoveEnd: m, scaleExtent: [e3, o3], translateExtent: c3, zoom: n3 });
  return import_react2.default.createElement(x2, { value: { x: h.x, y: h.y, k: h.k, transformString: p } }, import_react2.default.createElement("g", { ref: g2 }, import_react2.default.createElement("rect", { width: k3, height: y3, fill: "transparent" }), import_react2.default.createElement("g", { ref: d3, transform: p, className: `rsm-zoomable-group ${l3}`, ...v3 }, f3)));
});
y2.displayName = "ZoomableGroup";

// node_modules/react-simple-maps/dist/index.es.js
var import_react3 = __toESM(require_react());
export {
  K as Annotation,
  N as ComposableMap,
  A as Geographies,
  C as Geography,
  x as Graticule,
  q as Line,
  y as MapContext,
  b as MapProvider,
  T as Marker,
  S as Sphere,
  l2 as ZoomPanContext,
  x2 as ZoomPanProvider,
  y2 as ZoomableGroup,
  k as useGeographies,
  j as useMapContext,
  E2 as useZoomPan,
  v2 as useZoomPanContext
};
//# sourceMappingURL=react-simple-maps.js.map
