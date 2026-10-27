data {
  int<lower=1> N;
  int<lower=1> S;  //stations
  vector[N] x;
  vector[N] y;
  vector[N] night;
  
  array[N] int<lower=1, upper=S> station;
}
parameters {
  vector<lower=0>[S] alpha;   // each own intercept, in seconds
  
  real<lower=0> beta;
  real<lower=0> sigma;
  real<lower=1> nu;           // small = real heavy tail

  real p_night;
}
model {
  //nu ~ gamma(2, 0.1);

  log(y) ~ student_t(nu, log(alpha[station] + beta * x) + p_night * night, sigma);

  //log(y) ~ student_t(nu, log(alpha[station] + beta * x), sigma); //prenight
}

