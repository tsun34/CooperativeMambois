"""
  KalmanFilter.py
  Abbie Lee | 16.30

  Implementation of a Kalman filter for position estimation using the position,
  velocity and quaternion sensor readings.

  Based on 16.30 Lec 19 Notes from Fall 2018
"""
import numpy as np

class KalmanFilter:
    def __init__(self, A, B, C, D, Rw, Rv, X0, U0):
        """
        Give matrices for an estimator of the form

        xhat' = Axhat + Bu + L(y - yhat)
        yhat = Cxhat + Du

        X0: initial state matrix
        U0: control input matrix

        type of all matrices is np.array
        """
        self.A = A
        self.B = B
        self.C = C
        self.D = D

        self.Xhat = X0
        self.U = U0

        # TODO(abbielee): check initialization of below matrices

        # Initialize covariance matrices
        self.P = self.init_p()              # Error covariance
        self.Rw = Rw                        # Process noise covariance
        self.Rv = Rv                        # Measurement noise covariance

        # Initialize estimation gains
        self.L = self.update_L()

        # Measurement matrices
        self.Yhat = np.array([np.dot(self.A, self.X)+(np.dot(self.D, self.U))])

    def init_P(self):
        """
        Computes initial state covariance matrix from

        P[0] = E[X0*X0.T]

        NOTE: expected value of a constant is just the constant
        """
        self.P = np.dot(self.X, self.X.T)

    def update_L(self):
        """
        Computes L[k] from P[k] and state matrices

        L[k] = AP[K]C.T(Rv + CP[k]C.T)^-1
        """
        M = np.inv(self.Rv  + np.dot(C, np.dot(self.P, C.T)))
        self.L = np.dot(A, np.dot(P, np.dot(C.T, M)))

        return None

    def update_estim(self, Y):
        """
        Computes next state estimate

        xhat[k+1] = Axhat[k] + Bu[k] + L[k](y[k] - yhat[k])
        P[k+1] = (A-L[k]C)P[k](A-L[k]C).T + Rv + L[k]RwL[k].T

        Y: numpy array of sensor values at timestep k
        """
        self.X = np.dot(A, X) + np.dot(B, U)

        Acl = A - np.dot(self.L, self.C)
        self.P = np.dot(Acl, np.dot(self.P, Acl.T)) + Rv + np.dot(self.L, np.dot(Rw, self.L))

        return None

    def get_state_estimate(self, Y, U):
        """
        Given sensor measurements and control input, return the state estimate
        """
        self.update_L()
        self.update_estim()

        return self.X

class MamboKalman(KalmanFilter):
    def __init__(self, X0, U0):
        """
        Initializes KalmanFilter for a parrot mambo

        Model based on dynamics equations in Pset 2 and linearized model
        in Lab 3 from 16.30 Fall 2018

        states: x y z yaw pitch roll xdot ydot zdot p q r
        """
        A = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, -9.81, 0.0, -.064, 0.0, 0.0, 0.0, .1382, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 9.81, 0.0, -0.64, 0.0, -.1382, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.1999, 0.0, -2.5898, 0.0, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9755, 0.0, 0.0, 0.0, -2.1056, 0.0],
                      [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.1715]])

        B = 10000 * np.array([[0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0],
                              [0.0015, 0.0, 0.0, 0.0],
                              [0.0, 0.0, 0.0, 1.7157],
                              [0.0, 0.0, 1.3949, 0.0],
                              [0.0, 1.0, 0.0, 0.0]])

        C = np.eye(12)

        D = np.zeros((12, 4))

        Rw = np.array([])

        Rv = np.array([])

        KalmanFilter.__init__(A, B, C, D, Rw, Rv, X0, U0)