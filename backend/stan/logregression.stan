data {
  int<lower=0> N;
  vector[N] x;
  vector[N] y;
}


parameters {
  real<lower=0> alpha;
  real<lower=0> beta;
  real<lower=0> sigma;
}
model {
  y ~ lognormal(log(alpha + beta * x), sigma);
}
