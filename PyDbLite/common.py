#
# common.py
#
# BSD licence
# Author : Bro <bro.development@gmail.com>
#

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

class Expression(object):

    def __init__(self, **kwargs):
        self.key = kwargs.get("key", None)
        self.value = kwargs.get("value", None)
        self.filter_value = self.value
        self.operator = kwargs.get("operator", None)

        if kwargs:
            if self.operator == Filter.operations.LIKE:
                self.filter_value = "'%%%s%%'" % self.value
            elif self.operator == Filter.operations.ILIKE:
                self.filter_value = "'*%s*'" % self.value
            elif self.operator == Filter.operations.IN:
                print("self.value:", self.value)
                self.filter_value = "('%s')" % "','".join(self.value)
                print("self.filter_value:", self.filter_value)
            else:
                if type(self.value) is bool:
                    self.filter_value = 1 if self.value else 0
                else:
                    self.filter_value = "'%s'" % self.value

    def filter_string(self):
        filter_str = "%s %s %s" % (self.key, self.operator, self.filter_value)
        return filter_str

    def filter(self):
        filter_str = "? %s ?" % (self.operator)
        filter_values = (self.key, self.operator, self.filter_value)
        return filter_str, filter_values

    def __str__(self):
        return self.filter_string()

class ExpressionGroup(object):

    def __init__(self):
        self.expression = None
        self.exp_group1 = None
        self.exp_group2 = None
        self.exp_operator = None

    def is_dummy(self):
        return self.expression is None and self.exp_operator is None

    def __or__(self, exp_group):
        if exp_group.is_dummy() or self.is_dummy():
            return exp_group if self.is_dummy() else self
        new_exp_group = ExpressionGroup()
        new_exp_group.exp_group1 = exp_group
        new_exp_group.exp_group2 = self
        new_exp_group.exp_operator = Filter.operations.OR
        return new_exp_group

    def __and__(self, exp_group):
        if exp_group.is_dummy() or self.is_dummy():
            return exp_group if self.is_dummy() else self
        new_exp_group = ExpressionGroup()
        new_exp_group.exp_group1 = exp_group
        new_exp_group.exp_group2 = self
        new_exp_group.exp_operator = Filter.operations.AND
        return new_exp_group

    def __str__(self):
        if self.is_dummy():
            return ""
        if self.expression:
            return self.expression.filter_string()
        else:
            return "((%s) %s (%s))" % (self.exp_group1.filter_string(), self.exp_operator,
                                       self.exp_group2.filter_string())

    def filter(self):
        if self.is_dummy():
            return "", []
        if self.expression:
            return self.expression.filter()
        else:
            group1_str, group1_values = self.exp_group1.filter()
            group2_str, group2_values = self.exp_group2.filter()
            filter_str = "((%s) %s (%s))" % (group1_str, self.exp_operator, group2_str)
            return filter_str, group1_values + group2_values

    def filter_string(self):
        return str(self)


class Filter(object):
    operations = enum(**{'AND':'AND', 'OR':'OR', 'LIKE':'LIKE', 'ILIKE':"GLOB", "IN":"IN", 'EQ':"=", 'NE':"!=", 'LT':"<", 'LE':"<=", 'GT':">", 'GE':">="})

    def __init__(self, db, key):
        self.db = db
        self.key = key
        self.expression_group = ExpressionGroup()

    def is_filtered(self):
        return not self.expression_group.is_dummy()

    def _comparison(self, value, operation):
        self.expression_group.expression = Expression(key=self.key, value=value, operator=operation)
        return self

    def like(self, value):
        return self._comparison(value, self.operations.LIKE)

    def ilike(self, value):
        return self._comparison(value, self.operations.ILIKE)

    def __eq__(self, value):
        # Iterable, so we use IN (X, X...) instead of =
        if hasattr(value, '__iter__') and type(value) is not str:
            return self._comparison(value, self.operations.IN)
        else:
            return self._comparison(value, self.operations.EQ)

    def __ne__(self, value):
        return self._comparison(value, self.operations.NE)

    def __lt__(self, value):
        return self._comparison(value, self.operations.LT)

    def __le__(self, value):
        return self._comparison(value, self.operations.LE)

    def __gt__(self, value):
        return self._comparison(value, self.operations.GT)

    def __ge__(self, value):
        return self._comparison(value, self.operations.GE)

    def __and__(self, other_filter):
        """
        Returns a new filter that combines this filter with other_filter with AND.
        """
        new_filter = Filter(self.db, None)
        new_filter.expression_group = self.expression_group & other_filter.expression_group
        return new_filter

    def __or__(self, other_filter):
        """
        Returns a new filter that combines this filter with other_filter with OR.
        """
        new_filter = Filter(self.db, None)
        new_filter.expression_group = self.expression_group | other_filter.expression_group
        return new_filter

    def __len__(self):
        if self.expression_group.is_dummy():
            count = len(self.db)
        else:
            count = self.db._len(db_filter=self.expression_group)
        return count

    def __iter__(self):
        if self.expression_group.is_dummy():
            res = self.db()
        else:
            res = self.db(self.expression_group)
        return iter(res)

    def __str__(self):
        if self.expression_group:
            return self.expression_group.filter_string()
        else:
            return ""

    def filter(self):
        if self.expression_group:
            return self.expression_group.filter()
        else:
            return "", []
